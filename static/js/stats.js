document.addEventListener('DOMContentLoaded', () => {
    const searchBtn = document.getElementById('search-btn');
    const searchInput = document.getElementById('singer-name');
    
    searchBtn.addEventListener('click', () => {
        const name = searchInput.value.trim();
        if (name) {
            searchSinger(name);
        }
    });

    // Allow Enter key
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const name = searchInput.value.trim();
            if (name) {
                searchSinger(name);
            }
        }
    });

    // Initial load
    searchSinger("杨丞琳");
});

async function searchSinger(name) {
    const songListEl = document.getElementById('song-list');
    const singerInfoEl = document.getElementById('singer-info');
    
    // Show loading
    songListEl.innerHTML = '<div style="text-align: center; color: rgba(255,255,255,0.5); margin-top: 50px;">正在加载数据...</div>';
    singerInfoEl.style.display = 'none';

    try {
        const response = await fetch(`/api/search_singer?name=${encodeURIComponent(name)}`);
        const result = await response.json();

        if (result.code === 0 && result.data) {
            // Check for smart box info (zhida)
            const zhida = result.data.zhida;
            let singerData = null;
            let songs = [];

            if (zhida && zhida.zhida_singer) {
                singerData = zhida.zhida_singer;
                songs = singerData.hotsong || [];
            } else if (result.data.song && result.data.song.list) {
                // Fallback to song list if no exact singer match found in smart box
                // But usually we want singer info. 
                // If no singer info, we just show songs.
                songs = result.data.song.list;
            }

            if (singerData) {
                updateSingerInfo(singerData);
            }

            updateSongList(songs);
        } else {
            songListEl.innerHTML = '<div style="text-align: center; color: rgba(255,255,255,0.5); margin-top: 50px;">未找到相关数据</div>';
        }
    } catch (error) {
        console.error('Error:', error);
        songListEl.innerHTML = '<div style="text-align: center; color: rgba(255,255,255,0.5); margin-top: 50px;">加载失败，请重试</div>';
    }
}

function updateSingerInfo(data) {
    const singerInfoEl = document.getElementById('singer-info');
    const avatarEl = document.getElementById('singer-avatar');
    const titleEl = document.getElementById('singer-title');
    const songCountEl = document.getElementById('song-count');
    const albumCountEl = document.getElementById('album-count');

    avatarEl.src = data.singerPic;
    titleEl.textContent = data.singerName;
    songCountEl.textContent = data.songNum;
    albumCountEl.textContent = data.albumNum;

    singerInfoEl.style.display = 'flex';
}

function updateSongList(songs) {
    const songListEl = document.getElementById('song-list');
    songListEl.innerHTML = '';

    if (!songs || songs.length === 0) {
        songListEl.innerHTML = '<div style="text-align: center; color: rgba(255,255,255,0.5); margin-top: 50px;">暂无热门歌曲</div>';
        return;
    }

    songs.forEach(song => {
        const div = document.createElement('div');
        div.className = 'song-item';
        
        // Handle different song structures if necessary, but hotsong usually has songName, albumName
        const songName = song.songName || song.songname;
        const albumName = song.albumName || song.albumname;
        
        div.innerHTML = `
            <div class="song-info">
                <span class="song-name">${escapeHtml(songName)}</span>
                <span class="song-album">${escapeHtml(albumName)}</span>
            </div>
            <div class="song-action">♪</div>
        `;
        songListEl.appendChild(div);
    });
}

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
