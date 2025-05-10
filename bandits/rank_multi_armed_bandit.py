import os
from flask import Flask, request, jsonify
import numpy as np
from datetime import datetime
from entidades_rmab import db, Arm, BanditData, Tenant # Use db from entidades_rmab
from flask_cors import CORS

# Configuração do Flask e SQLAlchemy
app = Flask(__name__)
CORS(app)

# Database Configuration from Environment Variables
DB_TYPE = os.getenv('DB_TYPE', 'sqlite')
# Default base path for MAB SQLite DB from docker-compose.yml
DB_PATH_MAB_DEFAULT = '/app/instance/recommender.db'
# Default path for RMAB SQLite DB
DB_PATH_RMAB_DEFAULT = '/app/instance/recommender_rmab.db'

if DB_TYPE == 'sqlite':
    # For RMAB, we want recommender_rmab.db.
    # If DB_PATH is set, use its directory; otherwise, use the default RMAB path's directory.
    db_path_env = os.getenv('DB_PATH')
    if db_path_env:
        # Use the directory of the MAB DB_PATH and append the RMAB specific filename
        rmab_db_filename = 'recommender_rmab.db'
        DB_PATH = os.path.join(os.path.dirname(db_path_env), rmab_db_filename)
    else:
        # If DB_PATH is not set at all, use the full default RMAB path
        DB_PATH = DB_PATH_RMAB_DEFAULT
    
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
elif DB_TYPE == 'postgresql':
    DB_USER = os.getenv('DB_USER', 'user')
    DB_PASS = os.getenv('DB_PASS', 'password')
    DB_URL_HOST = os.getenv('DB_URL', 'postgres')
    DB_NAME = os.getenv('DB_NAME', 'recommender') # RMAB might need its own DB_NAME_RMAB or use schemas
    # For now, assume it uses the same DB but potentially different tables (handled by models)
    # Or, if they must be separate databases, a DB_NAME_RMAB env var would be needed.
    # The prompt implies using existing env vars. If RMAB needs a *separate* PG DB,
    # this setup will point to the same DB as MAB. This might be acceptable if table names
    # or schemas prevent clashes. Given `entidades_rmab.py` likely defines unique tables,
    # this should be fine.
    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASS}@{DB_URL_HOST}/{DB_NAME}'
else:
    raise ValueError(f"Unsupported DB_TYPE: {DB_TYPE}. Please set DB_TYPE to 'sqlite' or 'postgresql'.")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app) # Initialize db from entidades_rmab

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
def get_recommendation_ranked():
    tenant_id = request.args.get('tenant_id')
    profile_hash_base = request.args.get('profile_hash')
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

    k_actual = min(num_recommendations, len(all_arms_for_tenant))
    if k_actual == 0: # Should be caught by `not all_arms_for_tenant` but good for safety
        return jsonify({'error': 'No arms available to recommend for this tenant'}), 404
        
    ranked_recommendations = []
    selected_arm_ids_for_this_request = set()

    # Batch creation of BanditData entries if they don't exist
    new_bandit_data_entries_to_add = []

    for position_k in range(1, k_actual + 1):
        best_arm_for_this_position = None
        best_sample_for_this_position = -1
        candidate_arms = [arm for arm in all_arms_for_tenant if arm.id not in selected_arm_ids_for_this_request]
        
        if not candidate_arms:
            break

        for arm_candidate in candidate_arms:
            bandit_data_for_arm_position = BanditData.query.filter_by(
                tenant_id=tenant_id,
                profile_hash=composite_hash,
                arm_id=arm_candidate.id,
                position=position_k
            ).first()

            if not bandit_data_for_arm_position:
                # Create in memory, add to list for batch insertion
                bandit_data_for_arm_position = BanditData(
                    tenant_id=tenant_id,
                    profile_hash=composite_hash,
                    arm_id=arm_candidate.id,
                    position=position_k,
                    pulls=0,
                    rewards=0
                )
                new_bandit_data_entries_to_add.append(bandit_data_for_arm_position)
                # For Thompson sampling, use initial values as if it were just created
                alpha = 1
                beta = 1
            else:
                alpha = bandit_data_for_arm_position.rewards + 1
                beta = (bandit_data_for_arm_position.pulls - bandit_data_for_arm_position.rewards) + 1
            
            sample = np.random.beta(alpha, beta)

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

    if new_bandit_data_entries_to_add:
        db.session.add_all(new_bandit_data_entries_to_add)
        # Try to commit these new entries. If it fails, we might have an issue.
        # However, pull increments happen next, so committing all at once at the end is better.

    for rec_item in ranked_recommendations:
        bandit_data_entry = BanditData.query.filter_by(
            tenant_id=tenant_id,
            profile_hash=composite_hash,
            arm_id=rec_item['arm_id'],
            position=rec_item['position']
        ).first()

        # If it was just added to new_bandit_data_entries_to_add, it might not be in the session's
        # identity map yet if we haven't flushed/committed.
        # A robust way is to check our list or rely on the final commit.
        # For simplicity, we assume if it's not found by query, it's one we just decided to create.
        if not bandit_data_entry:
            # This implies it was one of the new_bandit_data_entries_to_add
            # Find it in the list to increment pulls.
            # This logic can be complex if not careful.
            # A simpler approach: ensure all BanditData objects (new or existing) are in the session,
            # then query/update. The current structure with pre-creation and then update is fine.
            # The key is that 'pulls' should be incremented on an object that will be committed.
            
            # Re-fetch or find in `new_bandit_data_entries_to_add`
            # This situation (not finding it after it should have been added to `new_bandit_data_entries_to_add`)
            # indicates a logic flaw if `db.session.add_all` and `db.session.commit` are not carefully placed.
            # Given the current flow, it *should* be found if it was in `new_bandit_data_entries_to_add`
            # *after* `db.session.add_all(new_bandit_data_entries_to_add)` and a potential flush/commit.
            # To be safe, let's re-check:
            found_in_new = next((bd for bd in new_bandit_data_entries_to_add if bd.arm_id == rec_item['arm_id'] and bd.position == rec_item['position']), None)
            if found_in_new:
                 bandit_data_entry = found_in_new # Use the in-memory object
            else:
                # This is problematic, means it wasn't created and wasn't existing.
                # For robustness, create it now if truly missing, though it implies an issue earlier.
                bandit_data_entry = BanditData(
                    tenant_id=tenant_id, profile_hash=composite_hash,
                    arm_id=rec_item['arm_id'], position=rec_item['position'],
                    pulls=0, rewards=0
                )
                db.session.add(bandit_data_entry) # Add to session if unexpectedly missing
        
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
def record_click_ranked():
    data_req = request.get_json()
    tenant_id = data_req.get('tenant_id')
    profile_hash_base = data_req.get('profile_hash')
    arm_id = data_req.get('arm_id')
    position_clicked = data_req.get('position') 

    if not all([tenant_id, profile_hash_base, arm_id is not None, position_clicked is not None]):
        return jsonify({'error': 'Missing parameters (tenant_id, profile_hash, arm_id, position are required)'}), 400

    try:
        position_int = int(position_clicked)
    except ValueError:
        return jsonify({'error': 'Position must be an integer'}), 400

    time_bin = get_time_bin()
    composite_hash = f"{profile_hash_base}_{time_bin}"

    bandit_data_clicked = BanditData.query.filter_by(
        tenant_id=tenant_id,
        profile_hash=composite_hash,
        arm_id=arm_id,
        position=position_int
    ).first()

    if bandit_data_clicked:
        bandit_data_clicked.rewards += 1
        db.session.commit()
        return jsonify({'status': 'success', 'message': f'Click recorded for arm {arm_id} at position {position_int}'})
    else:
        return jsonify({'error': f'Bandit data not found for arm {arm_id} at position {position_int} with hash {composite_hash}. Was it recommended in this context and position?'}), 404

@app.route('/tenant', methods=['POST'])
def create_tenant():
    data_req = request.get_json()
    tenant_id = data_req.get('tenant_id')

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
    data_req = request.get_json()
    tenant_id = data_req.get('tenant_id')
    arm_id = data_req.get('arm_id')
    name = data_req.get('name')

    if not all([tenant_id, arm_id is not None, name]):
        return jsonify({'error': 'tenant_id, arm_id e name são obrigatórios'}), 400

    if not Tenant.query.get(tenant_id):
        return jsonify({'error': 'Tenant não encontrado'}), 404

    if Arm.query.filter_by(tenant_id=tenant_id, id=arm_id).first():
        return jsonify({'error': 'Arm com este ID já existe para este tenant'}), 400

    arm = Arm(id=arm_id, tenant_id=tenant_id, name=name)
    db.session.add(arm)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Arm cadastrado com sucesso'}), 201

def run():
    # This function is not used in the current context but can be useful for testing
    # or if you want to run the app without using the Flask CLI.
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5001')), debug=True)

if __name__ == '__main__':
    # Port 5001 was used in the original prompt for RMAB.
    # This should align with how main.py or Docker setup intends to run it.
    app.run(host='0.0.0.0', port=int(os.getenv('PORT_RMAB', '5001')), debug=True)
