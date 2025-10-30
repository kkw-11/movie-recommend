"""
추천 엔진 - scikit-learn 기반
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('TMDB_API_KEY')
BASE_URL = 'https://api.themoviedb.org/3'

class RecommendationEngine:
    def __init__(self):
        self.movies = []
        self.similarity_matrix = None
        self.vectorizer = TfidfVectorizer(stop_words='english')
    
    def load_movies(self, num_pages=10):
        """TMDB에서 인기 영화 가져오기"""
        print(f"영화 데이터 로딩 중... (약 30초 소요)")
        
        for page in range(1, num_pages + 1):
            # 인기 영화 목록 가져오기
            url = f"{BASE_URL}/movie/popular"
            params = {
                'api_key': API_KEY,
                'language': 'ko-KR',
                'page': page
            }
            
            try:
                response = requests.get(url, params=params, timeout=5)
                results = response.json().get('results', [])
                
                # 각 영화의 상세 정보 가져오기
                for movie in results:
                    details = self._get_movie_details(movie['id'])
                    if details:
                        self.movies.append(details)
                
                print(f"  {page}/{num_pages} 페이지 완료 ({len(self.movies)}개 영화)")
                
            except Exception as e:
                print(f"  페이지 {page} 로딩 실패: {e}")
        
        print(f"✅ 총 {len(self.movies)}개 영화 로딩 완료!")
    
    def _get_movie_details(self, movie_id):
        """영화 상세 정보 가져오기"""
        url = f"{BASE_URL}/movie/{movie_id}"
        params = {
            'api_key': API_KEY,
            'language': 'ko-KR',
            'append_to_response': 'credits'
        }
        
        try:
            response = requests.get(url, params=params, timeout=5)
            return response.json()
        except:
            return None
    
    def _create_movie_features(self, movie):
        """영화를 텍스트 특징으로 변환"""
        features = []
        
        # 장르
        if 'genres' in movie:
            genres = ' '.join([g['name'] for g in movie['genres']])
            features.append(genres)
        
        # 감독
        if 'credits' in movie and 'crew' in movie['credits']:
            directors = ' '.join([
                crew['name'] for crew in movie['credits']['crew']
                if crew['job'] == 'Director'
            ])
            features.append(directors)
        
        # 배우 (상위 5명)
        if 'credits' in movie and 'cast' in movie['credits']:
            cast = ' '.join([
                actor['name'] for actor in movie['credits']['cast'][:5]
            ])
            features.append(cast)
        
        # 줄거리
        if movie.get('overview'):
            features.append(movie['overview'])
        
        return ' '.join(features)
    
    def build_similarity_matrix(self):
        """유사도 행렬 생성"""
        print("\n유사도 계산 중...")
        
        # 각 영화를 텍스트로 변환
        movie_features = [
            self._create_movie_features(movie) 
            for movie in self.movies
        ]
        
        # TF-IDF 벡터화
        tfidf_matrix = self.vectorizer.fit_transform(movie_features)
        
        # 코사인 유사도 계산
        self.similarity_matrix = cosine_similarity(tfidf_matrix)
        
        print(f"✅ 유사도 계산 완료! ({len(self.movies)}x{len(self.movies)} 행렬)")
    
    def get_recommendations(self, selected_movie_ids, n=20):
        """선택한 영화 기반 추천"""
        if not self.movies or self.similarity_matrix is None:
            return []
        
        # 영화 ID → 인덱스 매핑
        movie_id_to_idx = {
            movie['id']: idx 
            for idx, movie in enumerate(self.movies)
        }
        
        # 선택한 영화의 인덱스 찾기
        selected_indices = []
        for movie_id in selected_movie_ids:
            if movie_id in movie_id_to_idx:
                selected_indices.append(movie_id_to_idx[movie_id])
        
        if not selected_indices:
            return []
        
        # 선택한 영화들과의 평균 유사도 계산
        avg_similarity = self.similarity_matrix[selected_indices].mean(axis=0)
        
        # 유사도 높은 순으로 정렬
        similar_indices = avg_similarity.argsort()[::-1]
        
        # 추천 결과 생성 (이미 선택한 영화 제외)
        recommendations = []
        for idx in similar_indices:
            if idx not in selected_indices and len(recommendations) < n:
                movie = self.movies[idx].copy()
                movie['similarity_score'] = float(avg_similarity[idx])
                recommendations.append(movie)
        
        return recommendations
    
    def get_movie_by_id(self, movie_id):
        """ID로 영화 찾기"""
        for movie in self.movies:
            if movie['id'] == movie_id:
                return movie
        return None
