"""
Flask 서버 - 검색 + 추천
"""
from flask import Flask, jsonify, request, render_template
import requests
import os
from dotenv import load_dotenv
from recommendation_engine import RecommendationEngine

load_dotenv()
API_KEY = os.getenv('TMDB_API_KEY')
BASE_URL = 'https://api.themoviedb.org/3'

app = Flask(__name__)

# 추천 엔진 초기화 (서버 시작 시 1번만)
print("\n" + "=" * 50)
print("🎬 영화 추천 시스템 초기화")
print("=" * 50)

rec_engine = RecommendationEngine()
rec_engine.load_movies(num_pages=10)  # 200개 영화
rec_engine.build_similarity_matrix()

print("\n" + "=" * 50)
print("✅ 추천 엔진 준비 완료!")
print("=" * 50 + "\n")

@app.route('/')
def home():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/api/search')
def search_movies():
    """영화 검색 API"""
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({'error': '검색어를 입력해주세요'}), 400
    
    url = f"{BASE_URL}/search/movie"
    params = {
        'api_key': API_KEY,
        'query': query,
        'language': 'ko-KR',
        'page': 1
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        movies = []
        for movie in data.get('results', [])[:10]:
            movies.append({
                'id': movie['id'],
                'title': movie['title'],
                'original_title': movie.get('original_title', ''),
                'overview': movie.get('overview', ''),
                'release_date': movie.get('release_date', ''),
                'vote_average': movie.get('vote_average', 0),
                'poster_path': f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get('poster_path') else None
            })
        
        return jsonify({
            'query': query,
            'total_results': data.get('total_results', 0),
            'results': movies
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/movie/<int:movie_id>')
def get_movie_details(movie_id):
    """영화 상세 정보 API"""
    url = f"{BASE_URL}/movie/{movie_id}"
    params = {
        'api_key': API_KEY,
        'language': 'ko-KR',
        'append_to_response': 'credits'
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        movie = response.json()
        
        genres = [g['name'] for g in movie.get('genres', [])]
        
        directors = []
        if 'credits' in movie and 'crew' in movie['credits']:
            directors = [
                crew['name'] for crew in movie['credits']['crew']
                if crew['job'] == 'Director'
            ]
        
        cast = []
        if 'credits' in movie and 'cast' in movie['credits']:
            cast = [
                actor['name'] for actor in movie['credits']['cast'][:5]
            ]
        
        result = {
            'id': movie['id'],
            'title': movie['title'],
            'original_title': movie.get('original_title', ''),
            'overview': movie.get('overview', ''),
            'release_date': movie.get('release_date', ''),
            'vote_average': movie.get('vote_average', 0),
            'runtime': movie.get('runtime', 0),
            'genres': genres,
            'directors': directors,
            'cast': cast,
            'poster_path': f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get('poster_path') else None
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recommend', methods=['POST'])
def recommend():
    """추천 API (새로 추가!)"""
    data = request.json
    selected_movie_ids = data.get('movie_ids', [])
    
    if not selected_movie_ids:
        return jsonify({'error': '영화를 선택해주세요'}), 400
    
    if len(selected_movie_ids) < 3:
        return jsonify({'error': '최소 3개 이상 선택해주세요'}), 400
    
    # 추천 받기
    recommendations = rec_engine.get_recommendations(selected_movie_ids, n=20)
    
    # 결과 포맷팅
    result = []
    for movie in recommendations:
        result.append({
            'id': movie['id'],
            'title': movie['title'],
            'original_title': movie.get('original_title', ''),
            'overview': movie.get('overview', ''),
            'release_date': movie.get('release_date', ''),
            'vote_average': movie.get('vote_average', 0),
            'similarity_score': movie.get('similarity_score', 0),
            'genres': [g['name'] for g in movie.get('genres', [])],
            'poster_path': f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get('poster_path') else None
        })
    
    return jsonify({
        'selected_count': len(selected_movie_ids),
        'recommendations': result
    })

if __name__ == '__main__':
    print("\n🎬 영화 추천 웹 서비스 시작!")
    print("=" * 50)
    print("브라우저에서 열기: http://localhost:5001")
    print("=" * 50)
    print("\n종료: Ctrl + C\n")
    
    app.run(debug=True, host='0.0.0.0', port=5001)
