#!/bin/bash

# 환경 변수 로드
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 이전 컨테이너 정리
echo "Cleaning up previous containers..."
docker-compose down

# 이미지 빌드
echo "Building images..."
docker-compose build

# 컨테이너 시작
echo "Starting containers..."
docker-compose up -d

# 데이터베이스 마이그레이션
echo "Running database migrations..."
docker-compose exec api python data_migration.py

echo "Deployment completed successfully!"
echo "API is available at http://localhost:8000"
echo "API documentation is available at http://localhost:8000/api/docs" 