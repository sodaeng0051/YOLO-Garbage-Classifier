import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from ultralytics import YOLO
import cv2 # OpenCV for drawing

# 1. 환경 설정
DB_NAME = 'garbage_guide.db'
UPLOAD_FOLDER = 'static/uploads'
OUTPUT_FOLDER = 'static/images/results'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
YOLO_MODEL_PATH = 'static/models/best.pt' # Fine-tuned YOLOv8 모델 경로

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# 2. 모델 로드 및 DB 연결 테스트
try:
    # YOLOv8 모델 로드 (추가 학습 모델 가산점 3점)
    yolo_model = YOLO(YOLO_MODEL_PATH)
    print("--- YOLOv8 모델 로드 완료 ---")
    
    # DB 연결 테스트
    conn = sqlite3.connect(DB_NAME)
    conn.close()
    print("--- SQLite DB 연결 확인 완료 ---")

except FileNotFoundError:
    print("--- [오류]: 모델 파일 (best.pt) 또는 DB 파일 (garbage_guide.db)이 없습니다. ---")
    print("--- 1. YOLOv8 모델을 학습하거나 다운로드하여 'static/models/best.pt'에 저장하세요. ---")
    print("--- 2. 'db_setup.py'를 먼저 실행하여 DB를 생성하세요. ---")
    exit(1)
except Exception as e:
    print(f"--- 로드 중 오류 발생: {e} ---")
    exit(1)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# app.py 파일 수정

def get_guide_info(class_name):
    """DB에서 쓰레기 종류별 분리수거 가이드 정보를 가져옵니다."""
    
    # --- [수정] DB 조회 전에 클래스 이름을 대문자로 변환하여 통일 ---
    db_key = class_name.upper()
    # -----------------------------------------------------------
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 쿼리 실행 시 db_key 사용
    cursor.execute("SELECT recycle_guide, recycle_type, collection_day FROM guide WHERE class_name=?", (db_key,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'guide': result[0],
            'type': result[1],
            'day': result[2]
        }
    
    # 디버깅을 위해 정보가 없을 경우 로그를 남깁니다.
    print(f"ERROR: DB에서 클래스 [{db_key}]의 정보를 찾을 수 없습니다.")
    return None

def analyze_garbage_image(image_path):
    """YOLOv8 탐지 및 DB 정보 조회를 수행합니다."""
    
    # 1. YOLOv8 객체 탐지 및 분류
    # YOLOv8은 탐지(detection)와 분류(classification)를 동시에 수행
    results = yolo_model(image_path, conf=0.5, verbose=False)
    
    img = cv2.imread(image_path)
    analysis_results = []
    detected_classes = set()

    for r in results:
        boxes = r.boxes.xyxy.cpu().numpy()
        classes = r.boxes.cls.cpu().numpy()
        
        for box, cls in zip(boxes, classes):
            x1, y1, x2, y2 = map(int, box)
            class_name = yolo_model.names[int(cls)]
            detected_classes.add(class_name)

            # --- [추가] DB 조회 직전에 클래스 이름 확인 ---
            print(f"DEBUG: YOLO 모델이 탐지한 클래스 이름: {class_name}")
            # ----------------------------------------------
            
            # 2. 결과 시각화 (이미지 입출력 가산점 3점)
            color = (255, 0, 0) # BGR: Blue
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            
            text = f"{class_name}"
            cv2.putText(img, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            # 3. DB 정보 조회
            guide_info = get_guide_info(class_name)
            
            analysis_results.append({
                'class': class_name,
                'guide_info': guide_info if guide_info else {"guide": "분리수거 정보 없음", "type": "기타", "day": "-"},
                'box': (x1, y1, x2, y2)
            })

    # 결과 이미지 저장
    output_filename = os.path.basename(image_path).replace('.', f'_analyzed.')
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
    cv2.imwrite(output_path, img)

    # 중복 제거된 클래스에 대한 가이드 정보만 웹 출력에 사용
    final_guides = {}
    for cls in detected_classes:
        guide_info = get_guide_info(cls)
        final_guides[cls] = guide_info if guide_info else {"guide": "분리수거 정보 없음", "type": "기타", "day": "-"}

    return output_path.replace('static/', ''), final_guides

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(upload_path)

            # 4. 분석 수행 (입력 - 추론 - 출력의 핵심)
            result_img_path, guide_results = analyze_garbage_image(upload_path)
            
            return render_template('index.html', 
                                   uploaded_img=upload_path.replace('static/', ''), 
                                   result_img=result_img_path, 
                                   guide_results=guide_results)
    
    return render_template('index.html', uploaded_img=None, result_img=None, guide_results=None)

if __name__ == '__main__':
    # 필요한 폴더 생성
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
    if not os.path.exists('static/models'):
        os.makedirs('static/models')
        
    app.run(debug=True)