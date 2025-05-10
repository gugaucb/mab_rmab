import os
from flask import Flask, request, jsonify
import numpy as np
from datetime import datetime
from Entidades_mab import db, Arm, BanditData, Tenant # Use db from Entidades_mab
from flask_cors import CORS

# Configuração do Flask e SQLAlchemy
app = Flask(__name__)
CORS(app)

# Database Configuration from Environment Variables
DB_TYPE = os.getenv('DB_TYPE', 'sqlite')
# Default path for MAB SQLite DB, aligns with docker-compose.yml if DB_PATH is not set
DB_PATH_MAB_DEFAULT = '/app/instance/recommender.db'

if DB_TYPE == 'sqlite':
    DB_PATH = os.getenv('DB_PATH', DB_PATH_MAB_DEFAULT)
    # Ensure directory for SQLite DB exists
    db_dir = os.path.dirname(DB_PATH)
    if db_dir: # Check if db_dir is not empty (e.g. if DB_PATH is just a filename)
        os.makedirs(db_dir, exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
elif DB_TYPE == 'postgresql':
    DB_USER = os.getenv('DB_USER', 'user')
    DB_PASS = os.getenv('DB_PASS', 'password')
    DB_URL_HOST = os.getenv('DB_URL', 'postgres') # DB_URL from compose is the service name/host
    DB_NAME = os.getenv('DB_NAME', 'recommender')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASS}@{DB_URL_HOST}/{DB_NAME}'
else:
    # Fallback or error for unsupported DB_TYPE
    # For now, let's default to a safe SQLite path if DB_TYPE is unknown, or raise error
    # As per docker-compose, only sqlite and postgresql are expected.
    raise ValueError(f"Unsupported DB_TYPE: {DB_TYPE}. Please set DB_TYPE to 'sqlite' or 'postgresql'.")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app) # Initialize db from Entidades_mab

with app.app_context():
    db.create_all()

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

    time_bin = get_time_bin()
    composite_hash = f"{profile_hash}_{time_bin}"

    arms = Arm.query.filter_by(tenant_id=tenant_id).all()
    if not arms:
        return jsonify({'error': 'No arms found for tenant'}), 404

    best_arm = None
    best_sample = -1

    for arm_candidate in arms:
        data = BanditData.query.filter_by(
            tenant_id=tenant_id,
            profile_hash=composite_hash,
            arm_id=arm_candidate.id  # Corrected to arm_candidate.id
        ).first()

        if not data:
            data = BanditData(
                tenant_id=tenant_id,
                profile_hash=composite_hash,
                arm_id=arm_candidate.id, # Corrected to arm_candidate.id
                pulls=0,
                rewards=0
            )
            db.session.add(data)
            db.session.commit() # Commit to ensure data is queryable for update later

        alpha = data.rewards + 1
        beta = (data.pulls - data.rewards) + 1
        sample = np.random.beta(alpha, beta)

        if sample > best_sample:
            best_sample = sample
            best_arm = arm_candidate # Corrected to arm_candidate

    if best_arm:
        # Fetch the BanditData for the chosen best_arm to update its pulls
        bandit_data_to_update = BanditData.query.filter_by(
            tenant_id=tenant_id,
            profile_hash=composite_hash,
            arm_id=best_arm.id
        ).first()
        
        if bandit_data_to_update: # Should exist due to the loop above
            bandit_data_to_update.pulls += 1
            db.session.commit()
            return jsonify({'arm_id': best_arm.id, 'name': best_arm.name})
        else:
            # This case should ideally not be reached
            return jsonify({'error': 'Failed to find bandit data for update after selection'}), 500
            
    else:
        return jsonify({'error': 'No arm selected'}), 500

@app.route('/click', methods=['POST'])
def record_click():
    data_req = request.get_json()
    tenant_id = data_req.get('tenant_id')
    profile_hash = data_req.get('profile_hash')
    arm_id = data_req.get('arm_id')
    clicked = data_req.get('clicked', False) 

    if not all([tenant_id, profile_hash, arm_id is not None]): # arm_id can be 0
        return jsonify({'error': 'Missing parameters'}), 400

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
        return jsonify({'error': 'Bandit data not found for click recording'}), 404

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

    if not all([tenant_id, arm_id is not None, name]): # arm_id can be 0
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
    # For direct execution, listen on all interfaces, port as per Docker or local preference
    # The port 80 is often privileged; 5000 is a common Flask default.
    # Dockerfile exposes 80, so if main.py runs this, it should match.
    # If running this file directly (e.g. python bandits/multi_armed_bandit.py),
    # it might conflict with rank_multi_armed_bandit.py if it also tries to run on port 80.
    # For now, assume main.py handles execution.
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), debug=True)
