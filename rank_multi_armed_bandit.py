from flask import Flask, request, jsonify
import numpy as np
from datetime import datetime
from entidades_rmab import db, Arm, BanditData, Tenant # Assume que Entidades.py está no mesmo nível
# from flask_sqlalchemy import SQLAlchemy # Já importado via Entidades.db
from flask_cors import CORS

# Configuração do Flask e SQLAlchemy
app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recommender_rmab.db' # Novo nome de BD para não conflitar
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

K_RECOMMENDATIONS = 3 # Quantos itens rankeados retornar

def get_time_bin():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return 'morning'
    elif 12 <= hour < 18:
        return 'afternoon'
    else:
        return 'evening'

@app.route('/recommendation')
def get_recommendation_ranked(): # Nome da função alterado para clareza
    tenant_id = request.args.get('tenant_id')
    profile_hash_base = request.args.get('profile_hash') # Renomeado para clareza
    num_recommendations_str = request.args.get('k', str(K_RECOMMENDATIONS))

    try:
        num_recommendations = int(num_recommendations_str)
        if num_recommendations <= 0:
            num_recommendations = K_RECOMMENDATIONS
    except ValueError:
        num_recommendations = K_RECOMMENDATIONS


    if not tenant_id or not profile_hash_base:
        return jsonify({'error': 'Missing tenant_id or profile_hash'}), 400

    time_bin = get_time_bin()
    composite_hash = f"{profile_hash_base}_{time_bin}"

    all_arms_for_tenant = Arm.query.filter_by(tenant_id=tenant_id).all()
    if not all_arms_for_tenant:
        return jsonify({'error': 'No arms found for tenant'}), 404

    # Garantir que não tentemos recomendar mais arms do que os disponíveis
    k_actual = min(num_recommendations, len(all_arms_for_tenant))
    if k_actual == 0:
        return jsonify({'error': 'No arms available to recommend for this tenant'}), 404
        
    ranked_recommendations = []
    selected_arm_ids_for_this_request = set() # Para não recomendar o mesmo arm múltiplas vezes na MESMA lista

    for position_k in range(1, k_actual + 1): # Posições de 1 a K
        best_arm_for_this_position = None
        best_sample_for_this_position = -1

        # Iterar sobre os arms AINDA NÃO SELECIONADOS para esta requisição
        candidate_arms = [arm for arm in all_arms_for_tenant if arm.id not in selected_arm_ids_for_this_request]
        
        if not candidate_arms: # Não há mais arms para preencher as posições
            break

        for arm_candidate in candidate_arms:
            # Dados específicos para este arm NESTA POSIÇÃO
            bandit_data_for_arm_position = BanditData.query.filter_by(
                tenant_id=tenant_id,
                profile_hash=composite_hash,
                arm_id=arm_candidate.id,
                position=position_k # Crucial: filtrar pela posição atual
            ).first()

            if not bandit_data_for_arm_position:
                bandit_data_for_arm_position = BanditData(
                    tenant_id=tenant_id,
                    profile_hash=composite_hash,
                    arm_id=arm_candidate.id,
                    position=position_k,
                    pulls=0,
                    rewards=0
                )
                db.session.add(bandit_data_for_arm_position)
                # Commit pode ser adiado para o final, mas para Thompson Sampling com novos dados é bom ter
                # o objeto já persistido ou, pelo menos, os valores default corretos para alpha/beta.
                # Se não commitar aqui, alpha e beta serão baseados em 0+1, 0+1.
                # Vamos commitar no final do request para otimizar escritas.
                # db.session.commit() # Comentar para commitar em lote depois

            alpha = bandit_data_for_arm_position.rewards + 1
            beta = max(0, bandit_data_for_arm_position.pulls - bandit_data_for_arm_position.rewards) + 1
            sample = np.random.beta(alpha, beta)
            
            # Debug: print(f"Pos: {position_k}, Arm: {arm_candidate.name}, Alpha: {alpha}, Beta: {beta}, Sample: {sample:.4f}")

            if sample > best_sample_for_this_position:
                best_sample_for_this_position = sample
                best_arm_for_this_position = arm_candidate
        
        if best_arm_for_this_position:
            ranked_recommendations.append({
                'arm_id': best_arm_for_this_position.id,
                'name': best_arm_for_this_position.name,
                'position': position_k
            })
            selected_arm_ids_for_this_request.add(best_arm_for_this_position.id)
        else:
            # Não deveria acontecer se candidate_arms não estiver vazio,
            # a menos que todos os samples sejam -1 (improvável).
            # Ou se não houver candidate_arms, já tratamos com o 'break'
            pass 
            
    # Agora, incrementar 'pulls' para todos os (arm, position) que foram mostrados
    # e commitar as novas entradas BanditData
    for rec_item in ranked_recommendations:
        # Busca ou cria o bandit_data para o caso de não ter sido criado no loop (se adiamos o commit)
        bandit_data_entry = BanditData.query.filter_by(
            tenant_id=tenant_id,
            profile_hash=composite_hash,
            arm_id=rec_item['arm_id'],
            position=rec_item['position']
        ).first()

        if not bandit_data_entry: # Deveria ter sido criado no loop acima se não existia
             bandit_data_entry = BanditData(
                    tenant_id=tenant_id,
                    profile_hash=composite_hash,
                    arm_id=rec_item['arm_id'],
                    position=rec_item['position'],
                    pulls=0, # Será incrementado para 1
                    rewards=0
                )
             db.session.add(bandit_data_entry)
        
        bandit_data_entry.pulls += 1
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Database commit error: {str(e)}'}), 500

    if not ranked_recommendations:
        return jsonify({'error': 'No arms could be selected for ranking'}), 500
        
    return jsonify(ranked_recommendations)


@app.route('/click', methods=['POST'])
def record_click_ranked(): # Nome da função alterado para clareza
    data = request.get_json()
    tenant_id = data.get('tenant_id')
    profile_hash_base = data.get('profile_hash')
    arm_id = data.get('arm_id')
    # AGORA PRECISAMOS DA POSIÇÃO DO ITEM CLICADO
    position_clicked = data.get('position') 
    # 'clicked' continua sendo um booleano, mas implicitamente um clique é sempre True
    # Se você quiser registrar "viu mas não clicou", o frontend teria que enviar isso.
    # Para RMAB, geralmente só nos importamos com cliques positivos.

    if not all([tenant_id, profile_hash_base, arm_id, position_clicked is not None]):
        return jsonify({'error': 'Missing parameters (tenant_id, profile_hash, arm_id, position are required)'}), 400

    try:
        position_int = int(position_clicked)
    except ValueError:
        return jsonify({'error': 'Position must be an integer'}), 400

    time_bin = get_time_bin()
    composite_hash = f"{profile_hash_base}_{time_bin}"

    # A recompensa é para o arm NA POSIÇÃO em que foi clicado
    bandit_data_clicked = BanditData.query.filter_by(
        tenant_id=tenant_id,
        profile_hash=composite_hash,
        arm_id=arm_id,
        position=position_int # Usar a posição do clique
    ).first()

    if bandit_data_clicked:
        # Assumimos que se este endpoint é chamado, é um clique positivo (recompensa)
        bandit_data_clicked.rewards += 1
        db.session.commit()
        return jsonify({'status': 'success', 'message': f'Click recorded for arm {arm_id} at position {position_int}'})
    else:
        # Isso pode acontecer se o item clicado não foi um dos que o sistema acabou de recomendar
        # ou se houve alguma inconsistência de dados (ex: profile_hash mudou rapidamente).
        return jsonify({'error': f'Bandit data not found for arm {arm_id} at position {position_int} with hash {composite_hash}. Was it recommended in this context and position?'}), 404

# As rotas /tenant e /arm permanecem as mesmas, pois não são diretamente afetadas pelo RMAB
@app.route('/tenant', methods=['POST'])
def create_tenant():
    data = request.get_json()
    tenant_id = data.get('tenant_id')

    if not tenant_id:
        return jsonify({'error': 'tenant_id é obrigatório'}), 400

    if Tenant.query.get(tenant_id):
        return jsonify({'error': 'Tenant já existe'}), 400

    tenant = Tenant(id=tenant_id)
    db.session.add(tenant)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Tenant cadastrado com sucesso'}), 201


@app.route('/arm', methods=['POST'])
def create_arm():
    data = request.get_json()
    tenant_id = data.get('tenant_id')
    arm_id = data.get('arm_id')
    name = data.get('name')

    if not all([tenant_id, arm_id, name]):
        return jsonify({'error': 'tenant_id, arm_id e name são obrigatórios'}), 400

    if not Tenant.query.get(tenant_id):
        return jsonify({'error': 'Tenant não encontrado'}), 404

    if Arm.query.filter_by(tenant_id=tenant_id, id=arm_id).first():
        return jsonify({'error': 'Arm já existe para este tenant'}), 400

    arm = Arm(id=arm_id, tenant_id=tenant_id, name=name)
    db.session.add(arm)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Arm cadastrado com sucesso'}), 201

if __name__ == '__main__':
    app.run(debug=True, port=5001) # Rodar em porta diferente para não conflitar com o original