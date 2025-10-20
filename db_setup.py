import sqlite3
import json

DB_NAME = 'garbage_guide.db'

# 쓰레기 분류 클래스와 분리수거 가이드 정보
GUIDE_DATA = {
    "CAN": {
        "guide": "내용물을 비우고 물로 헹군 후, 압축하여 배출합니다. 부탄가스 등은 구멍을 뚫어 내용물을 완전히 비웁니다.",
        "type": "고철/캔류",
        "day": "매주 수요일"
    },
    "PLASTIC": {
        "guide": "내용물을 비우고 깨끗이 헹군 후, 라벨을 제거하고 찌그러트려 뚜껑을 닫아 배출합니다.",
        "type": "플라스틱류",
        "day": "매주 화요일"
    },
    "PAPER": {
        "guide": "물기에 젖지 않도록 펴서 묶어 배출하며, 스프링 등 이물질은 제거합니다.",
        "type": "종이류",
        "day": "매주 목요일"
    },
    "GLASS": {
        "guide": "병뚜껑을 제거하고, 내용물을 비운 후 배출합니다. 깨진 유리는 신문지에 싸서 종량제 봉투에 버립니다.",
        "type": "유리병류",
        "day": "매월 셋째주 월요일"
    }
}

def create_db():
    """SQLite 데이터베이스를 생성하고 가이드 정보를 입력합니다."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 테이블 생성
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guide (
            class_name TEXT PRIMARY KEY,
            recycle_guide TEXT NOT NULL,
            recycle_type TEXT NOT NULL,
            collection_day TEXT
        )
    ''')

    # 데이터 삽입
    for class_name, data in GUIDE_DATA.items():
        cursor.execute('''
            INSERT OR REPLACE INTO guide (class_name, recycle_guide, recycle_type, collection_day)
            VALUES (?, ?, ?, ?)
        ''', (class_name, data['guide'], data['type'], data['day']))

    conn.commit()
    conn.close()
    print(f"--- SQLite DB ({DB_NAME}) 및 쓰레기 가이드 정보 구축 완료 ---")

if __name__ == '__main__':
    create_db()