import os
from flask import Flask, jsonify, request
import requests
import firebase_admin
from firebase_admin import credentials, firestore, auth
from dotenv import load_dotenv
import base64
import json
import time
import uuid
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


load_dotenv()

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

# app.py의 /process/ocr-request 함수

# app.py 파일에 아래 함수를 통째로 붙여넣으세요.
# 함수 바깥에 있는 다른 import 구문이나 app = Flask(__name__) 등은 그대로 두셔야 합니다.

@app.route("/process/ocr-request", methods=['POST'])
def process_ocr_request():
    # --- 1. 클라이언트로부터 파일 수신 및 기본 검증 ---
    if 'file' not in request.files:
        return jsonify(status="error", message="No file part in the request"), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify(status="error", message="No file selected for uploading"), 400

    # --- 2. 네이버 클로바 OCR API 요청 데이터 구성 ---
    secret_key = os.environ.get('NCP_SECRET_KEY')
    api_url = os.environ.get('NCP_APIGW_URL')

    if not secret_key or not api_url:
        return jsonify(status="error", message="Server environment variables are not set"), 500

    # --- 2a. 파일 확장자 안전하게 추출 및 검증 ---
    filename = file.filename
    if '.' in filename:
        # 파일 이름의 오른쪽에서부터 점(.)을 딱 한 번만 찾아 분리하고, 확장자를 소문자로 변환
        format_extension = filename.rsplit('.', 1)[1].lower()
    else:
        # 파일 이름에 확장자가 없는 경우, 기본값으로 'jpg'를 사용 (또는 오류 처리)
        format_extension = 'jpg'

    # 네이버 API가 허용하는 확장자 목록
    allowed_formats = ['jpg', 'jpeg', 'png', 'tif', 'tiff', 'pdf']
    if format_extension not in allowed_formats:
        # 추출한 확장자가 허용 목록에 없으면 오류 반환
        return jsonify(status="error", message=f"Unsupported file format: {format_extension}"), 400

    # --- 2b. API 요청 본문(JSON) 및 파일 데이터 구성 ---
    request_json = {
        'images': [
            {
                'format': format_extension,
                'name': 'receipt'  # 인식할 이미지의 별명
            }
        ],
        'requestId': str(uuid.uuid4()),
        'version': 'V2',
        'timestamp': int(time.time() * 1000)
    }

    # 요청 데이터를 multipart/form-data 형식으로 구성
    payload = {'message': json.dumps(request_json).encode('UTF-8')}
    files = [
        ('file', file.read())
    ]
    
    headers = {
        "X-OCR-SECRET": secret_key
    }

    # --- 3. API 호출 및 결과 반환 ---
    try:
        response = requests.post(api_url, headers=headers, data=payload, files=files)
        # HTTP 오류 코드가 4xx 또는 5xx이면 예외 발생
        response.raise_for_status()
        
        ocr_result = response.json()
        
        return jsonify(status="success", data=ocr_result)

    except requests.exceptions.RequestException as e:
        # 요청 실패 시, 더 상세한 오류 메시지를 포함하여 반환
        error_details = {"error_message": str(e)}
        if e.response is not None:
            try:
                # 응답 본문이 JSON 형태일 경우, 내용을 error_details에 추가
                error_details.update(e.response.json())
            except json.JSONDecodeError:
                # JSON이 아닐 경우, 텍스트 내용을 그대로 추가
                error_details["response_text"] = e.response.text
        
        return jsonify(status="error", message="API request failed", details=error_details), 500
    except Exception as e:
        # 그 외 예측하지 못한 서버 내부 오류
        return jsonify(status="error", message=f"An unexpected error occurred: {str(e)}"), 500

app.route("/auth/google", methods=['POST'])
def google_auth():
    # 1. 클라이언트가 보낸 ID 토큰 받기
    id_token = request.json.get('token')
    if not id_token:
        return jsonify(status="error", message="No ID token provided"), 400

    try:
        # 2. Firebase Admin SDK로 ID 토큰 검증
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        
        # 3. Firestore 'users' 컬렉션에서 사용자 정보 확인 또는 생성
        user_ref = db.collection('users').document(uid)
        user_doc = user_ref.get()
        
        current_time = firestore.SERVER_TIMESTAMP

        if user_doc.exists:
            # 이미 가입된 사용자: 마지막 로그인 시간 업데이트
            user_ref.update({'lastLoginAt': current_time})
            user_data = user_doc.to_dict()
            message = "User authenticated successfully."
        else:
            # 새로운 사용자: 사용자 정보 생성
            user_data = {
                'email': decoded_token.get('email'),
                'displayName': decoded_token.get('name'),
                'createdAt': current_time,
                'lastLoginAt': current_time
            }
            user_ref.set(user_data)
            message = "New user created and authenticated successfully."

        return jsonify(status="success", message=message, data=user_data)

    except auth.InvalidIdTokenError:
        # 토큰이 유효하지 않을 때 (만료, 변조 등)
        return jsonify(status="error", message="Invalid ID token"), 401
    except Exception as e:
        return jsonify(status="error", message=f"An unexpected error occurred: {str(e)}"), 500
if __name__ == '__main__':
    app.run(debug=True, port=5001)