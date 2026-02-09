import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

# LangChain 관련 임포트
# ★ 수정됨: PyPDFLoader 대신 더 강력한 PDFPlumberLoader 사용
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

# 1. 환경변수 로드
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, ".env"))

if not os.getenv("OPENAI_API_KEY"):
    print("❌ OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")
    exit()

# 2. 경로 설정
DATA_PATH = os.path.join(BASE_DIR, "database", "RAG_data", "AI_engineer")
DB_PATH = os.path.join(BASE_DIR, "chroma_db")

def main():
    print(f"📂 데이터 경로: {DATA_PATH}")
    print(f"💾 DB 저장 경로: {DB_PATH}")

    # 3. 기존 DB 삭제
    if os.path.exists(DB_PATH):
        try:
            shutil.rmtree(DB_PATH)
            print("🗑️  기존 DB 삭제 완료 (초기화)")
        except PermissionError:
            print("⚠️  기존 DB를 삭제할 수 없습니다. 다른 프로그램(Python 등)이 폴더를 사용 중인지 확인하세요.")
            return

    all_documents = []
    
    # 4. 폴더 순회하며 PDF 로드
    if not os.path.exists(DATA_PATH):
        print(f"❌ 데이터 폴더를 찾을 수 없습니다: {DATA_PATH}")
        return

    company_folders = [d for d in os.listdir(DATA_PATH) if os.path.isdir(os.path.join(DATA_PATH, d))]
    
    print(f"🏢 발견된 기업 폴더: {company_folders}")

    for company in company_folders:
        company_path = os.path.join(DATA_PATH, company)
        files = [f for f in os.listdir(company_path) if f.endswith(".pdf")]
        
        print(f"   ㄴ [{company}] PDF {len(files)}개 처리 중...")

        for file in files:
            file_path = os.path.join(company_path, file)
            try:
                # ★ 로더 교체 부분
                loader = PDFPlumberLoader(file_path)
                docs = loader.load()
                
                # ★ 디버깅: 텍스트가 진짜 읽혔는지 확인 (첫 번째 페이지만)
                if docs and len(docs[0].page_content.strip()) > 0:
                    pass # 정상
                else:
                    print(f"      ⚠️  경고: '{file}' 파일에서 텍스트를 찾지 못했습니다. (이미지일 가능성 있음)")

                for doc in docs:
                    # 빈 페이지는 건너뜀
                    if not doc.page_content.strip():
                        continue
                        
                    doc.metadata["company"] = company
                    doc.metadata["source"] = file
                    all_documents.append(doc)
                    
            except Exception as e:
                print(f"      ❌ 파일 로드 실패 ({file}): {e}")

    if not all_documents:
        print("\n❌ [중단] 유효한 텍스트가 포함된 문서가 하나도 없습니다.")
        print("   -> PDF가 '이미지(스캔본)'인지 확인해보세요. 텍스트 드래그가 안 된다면 OCR이 필요합니다.")
        return

    print(f"\n✅ 유효한 텍스트 페이지 {len(all_documents)}장 확보됨.")
    # 샘플 출력
    print(f"   [샘플 텍스트]: {all_documents[0].page_content[:100]}...")

    # 5. 텍스트 청킹 (자르기)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )
    splits = text_splitter.split_documents(all_documents)
    print(f"✂️  청킹 완료: 총 {len(splits)}개의 조각(Chunks) 생성")

    if len(splits) == 0:
        print("❌ [오류] 청크가 0개입니다. 텍스트가 너무 짧거나 공백일 수 있습니다.")
        return

    # 6. 벡터 DB 생성 및 저장
    print("🚀 벡터 DB 생성 중... (잠시만 기다려주세요)")
    
    try:
        vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=OpenAIEmbeddings(),
            persist_directory=DB_PATH
        )
        print("\n🎉 DB 생성 성공! 'chroma_db' 폴더가 생성되었습니다.")
        
        # 7. 테스트 검색
        print("\n🔎 [테스트] DB 검색 시도...")
        test_retriever = vectorstore.as_retriever(search_kwargs={"k": 1})
        # DB에 있는 내용 아무거나 검색되도록 첫 번째 문서 내용으로 검색
        sample_query = splits[0].page_content[:20] 
        results = test_retriever.invoke(sample_query)
        
        if results:
            print(f"   결과 확인: {results[0].page_content[:50]}...")
        else:
            print("   결과 없음")
            
    except Exception as e:
        print(f"\n❌ DB 저장 중 오류 발생: {e}")

if __name__ == "__main__":
    main()