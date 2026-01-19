document.addEventListener('DOMContentLoaded', () => {
    const searchBtn = document.getElementById('search-btn');
    const searchInput = document.getElementById('singer-name');
    
    searchBtn.addEventListener('click', () => {
        const name = searchInput.value.trim();
        if (name) {
            searchSinger(name);
        }
    });

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
    
    // Reset / Loading State
    songListEl.innerHTML = '<div class="loading">正在获取实时数据...</div>';
    document.getElementById('total-songs').textContent = '-';
    document.getElementById('total-albums').textContent = '-';
    document.getElementById('total-mvs').textContent = '-';
    document.getElementById('total-collects').textContent = '-';

    try {
        const response = await fetch(`/api/search_singer?name=${encodeURIComponent(name)}`);
        const result = await response.json();

        if (result.code === 0 && result.data) {
            const stats = result.data.stats;
            const singer = result.data.singer;
            
            // Update Singer Info
            updateSingerInfo(singer, stats);

            // Update Stats Panel (using real data from tool.curleyg.info)
            document.getElementById('total-songs').textContent = stats.song_num || '-';
            document.getElementById('total-albums').textContent = stats.album_num || '-';
            document.getElementById('total-mvs').textContent = stats.mv_num || '-';
            
            // Format fans number or listen number if available
            // Note: tool.curleyg.info might return different fields, adjusting based on common structure
            // Let's use 'listen_num' if available for total collects area or similar
            if (stats.listen_num) {
                document.getElementById('total-collects').innerHTML = 
                    `${formatNumber(stats.listen_num)} <div style="font-size:0.6rem;opacity:0.6">当前收听</div>`;
            } else {
                 document.getElementById('total-collects').textContent = '-';
            }

            // Render Song List
            if (stats.songs && stats.songs.length > 0) {
                renderSongs(stats.songs);
            } else {
                songListEl.innerHTML = '<div class="loading">未找到歌曲数据</div>';
            }

        } else {
            songListEl.innerHTML = '<div class="loading">未找到相关数据</div>';
        }
    } catch (error) {
        console.error('Error:', error);
        songListEl.innerHTML = '<div class="loading">加载失败，请重试</div>';
    }
}

function updateSingerInfo(singer, stats) {
    document.getElementById('singer-title').textContent = singer.name || stats.singer_name;
    
    let picUrl = singer.pic || stats.singer_pic;
    if (picUrl) {
        // Try to get high-res image
        picUrl = picUrl.replace('150x150', '500x500').replace('300x300', '800x800');
        document.getElementById('singer-bg').style.backgroundImage = `url('${picUrl}')`;
    }
}

function renderSongs(songs) {
    const songListEl = document.getElementById('song-list');
    songListEl.innerHTML = '';
    
    songs.forEach((song, index) => {
        const div = document.createElement('div');
        div.className = 'song-item';
        
        // Data from tool.curleyg.info usually has these fields:
        // songname, albumname, listen_num (real-time), listen_num_last_day
        
        // Handle potential field naming differences
        const songName = song.songname || song.name;
        const albumName = song.albumname || song.album?.name || '';
        const listenNum = song.listen_num || 0;
        const listenLastDay = song.listen_num_last_day || 0;

        div.innerHTML = `
            <div class="song-main">
                <div class="song-title ${index < 3 ? 'active' : ''}">${index + 1}. ${escapeHtml(songName)}</div>
                <div class="song-meta">${escapeHtml(albumName)}</div>
            </div>
            <div class="song-stat">
                <div class="stat-row" title="昨日收听">
                    <i>📅</i>
                    <span class="stat-num pink">${formatNumber(listenLastDay)}</span>
                </div>
            </div>
            <div class="song-stat">
                <div class="stat-row" title="当前在听">
                    <i>🎧</i>
                    <span class="stat-num blue">${formatNumber(listenNum)}</span>
                </div>
            </div>
        `;
        songListEl.appendChild(div);
    });
}

function formatNumber(num) {
    if (!num) return '0';
    const n = parseInt(num);
    if (isNaN(n)) return num; // return as is if string
    
    if (n > 100000000) {
        return (n / 100000000).toFixed(2) + '亿';
    }
    if (n > 10000) {
        return (n / 10000).toFixed(1) + 'w';
    }
    return n.toString();
}

function escapeHtml(text) {
    if (!text) return '';
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
