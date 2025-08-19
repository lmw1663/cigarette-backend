import os
from flask import Flask, jsonify
import firebase_admin
from firebase_admin import credentials, firestore

# ---------- Firebase Admin SDK 초기화 ----------
# 로컬 개발 시: 다운로드한 json 키 파일 사용
# Render 배포 시: 환경 변수에 저장된 json 내용 사용
if os.path.exists('serviceAccountKey.json'):
    cred = credentials.Certificate('serviceAccountKey.json')
else:
    # Render 환경 변수에서 json 내용을 직접 읽어옴
    firebase_config_str = os.environ.get('FIREBASE_CONFIG_JSON')
    # 이 부분은 나중에 Render 설정 시 중요하게 사용됩니다.
    # 지금은 로컬 개발에 집중하므로 이 코드는 실행되지 않습니다.
    if firebase_config_str:
        import json
        firebase_config = json.loads(firebase_config_str)
        cred = credentials.Certificate(firebase_config)
    else:
        # 로컬에서도, 배포 환경에서도 키를 찾을 수 없을 때
        # 지금은 그냥 None으로 처리하고 넘어갑니다.
        cred = None

if cred:
    firebase_admin.initialize_app(cred)
    db = firestore.client()
# ----------------------------------------------


app = Flask(__name__)

app = Flask(__name__)

@app.route("/")
def health_check():
    return jsonify(status="ok", message="Server is running!")

@app.route("/data/cigarettes")
def get_all_cigarettes():
    try:
        # 'cigarettes' 컬렉션의 모든 문서를 가져옴
        brands_ref = db.collection('cigarettes').stream()
        all_cigarettes_data = []

        for brand_doc in brands_ref:
            brand_data = brand_doc.to_dict()
            products_data = []
            
            # 각 브랜드 문서 아래의 'products' 서브컬렉션을 가져옴
            products_ref = brand_doc.reference.collection('products').stream()
            for prod_doc in products_ref:
                products_data.append(prod_doc.to_dict())
            
            brand_data['products'] = products_data
            all_cigarettes_data.append(brand_data)

        return jsonify({
            "status": "success",
            "data": all_cigarettes_data
        })
    except Exception as e:
        # 에러 발생 시
        return jsonify(status="error", message=str(e)), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)