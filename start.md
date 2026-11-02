# Backend

cd D:\FixLens\backend
uvicorn app.main:create_app --factory --reload --host 0.0.0.0 --port 8000

# Frontend

cd D:\FixLens\mobile
npx expo start -c
