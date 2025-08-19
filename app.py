from flask import Flask, jsonify

# Flask 앱 생성
app = Flask(__name__)

# 루트('/') 주소로 GET 요청이 오면 이 함수를 실행
@app.route("/")
def health_check():
    # 서버가 살아있는지 확인하는 용도의 간단한 메시지를 JSON 형태로 반환
    return jsonify(
        status="ok",
        message="Server is running!"
    )

# 이 파일을 직접 실행했을 때 (예: python app.py) 서버를 개발 모드로 실행
if __name__ == '__main__':
    app.run(debug=True, port=5001)
