from flask import Flask, request, jsonify
import numpy as np
from datetime import datetime
from Entidades_mab import db, Arm, BanditData, Tenant
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
# Configuração do Flask e SQLAlchemy
app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recommender.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()
#app = Flask(__name__)
#app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@localhost/recommender'
#db.init_app(app)

def get_time_bin():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return 'morning'
    elif 12 <= hour < 18:
        return 'afternoon'
    else:
        return 'evening'

@app.route('/recommendation')
def get_recommendation():
    tenant_id = request.args.get('tenant_id')
    profile_hash = request.args.get('profile_hash')
    if not tenant_id or not profile_hash:
        return jsonify({'error': 'Missing tenant_id or profile_hash'}), 400

    # Adicionar contexto temporal
    time_bin = get_time_bin()
    composite_hash = f"{profile_hash}_{time_bin}"

    # Buscar todos os itens do menu para o tenant
    arms = Arm.query.filter_by(tenant_id=tenant_id).all()
    if not arms:
        return jsonify({'error': 'No arms found for tenant'}), 404

    best_arm = None
    best_sample = -1

    for arm in arms:
        data = BanditData.query.filter_by(
            tenant_id=tenant_id,
            profile_hash=composite_hash,
            arm_id=arm.id
        ).first()

        if not data:
            data = BanditData(
                tenant_id=tenant_id,
                profile_hash=composite_hash,
                arm_id=arm.id,
                pulls=0,
                rewards=0
            )
            db.session.add(data)
            db.session.commit()

        # Thompson Sampling
        alpha = data.rewards + 1
        beta = max(0, data.pulls - data.rewards) + 1
        print(f"Arm: {arm.name}, Alpha: {alpha}, Beta: {beta}")
        sample = np.random.beta(alpha, beta)

        if sample > best_sample:
            best_sample = sample
            best_arm = arm

    if best_arm:
        # Atualizar contagem de exposições
        bandit_data = BanditData.query.filter_by(
            tenant_id=tenant_id,
            profile_hash=composite_hash,
            arm_id=best_arm.id
        ).first()
        if not bandit_data:
            bandit_data = BanditData(
                tenant_id=tenant_id,
                profile_hash=composite_hash,
                arm_id=best_arm.id,
                pulls=1,
                rewards=0
            )
            db.session.add(bandit_data)
        else:
            bandit_data.pulls += 1
        db.session.commit()

        return jsonify({'arm_id': best_arm.id, 'name': best_arm.name})
    else:
        return jsonify({'error': 'No arm selected'}), 500

@app.route('/click', methods=['POST'])
def record_click():
    data = request.get_json()
    tenant_id = data.get('tenant_id')
    profile_hash = data.get('profile_hash')
    arm_id = data.get('arm_id')
    clicked = data.get('clicked', False)

    if not all([tenant_id, profile_hash, arm_id]):
        return jsonify({'error': 'Missing parameters'}), 400

    # Usar o mesmo contexto temporal do momento da recomendação
    time_bin = get_time_bin()
    composite_hash = f"{profile_hash}_{time_bin}"

    bandit_data = BanditData.query.filter_by(
        tenant_id=tenant_id,
        profile_hash=composite_hash,
        arm_id=arm_id
    ).first()

    if bandit_data:
        if clicked:
            bandit_data.rewards += 1
        db.session.commit()
        return jsonify({'status': 'success'})
    else:
        return jsonify({'error': 'Bandit data not found'}), 404


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
    app.run(debug=True) 
