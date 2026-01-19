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
    const singerTitleEl = document.getElementById('singer-title');
    const singerBgEl = document.getElementById('singer-bg');
    
    // Reset / Loading State
    songListEl.innerHTML = '<div class="loading">正在加载数据...</div>';
    document.getElementById('total-songs').textContent = '-';
    document.getElementById('total-albums').textContent = '-';
    document.getElementById('total-mvs').textContent = '-';
    document.getElementById('total-collects').textContent = '-';

    try {
        const response = await fetch(`/api/search_singer?name=${encodeURIComponent(name)}`);
        const result = await response.json();

        if (result.code === 0 && result.data) {
            // Check for smart box info (zhida) for singer details
            const zhida = result.data.zhida;
            let singerData = null;
            let songs = [];

            if (zhida && zhida.zhida_singer) {
                singerData = zhida.zhida_singer;
                songs = singerData.hotsong || [];
            } else if (result.data.song && result.data.song.list) {
                songs = result.data.song.list;
                // Try to extract singer info from the first song
                if (songs.length > 0 && songs[0].singer && songs[0].singer.length > 0) {
                    singerData = {
                        singerName: songs[0].singer[0].name,
                        singerPic: `https://y.gtimg.cn/music/photo_new/T001R150x150M000${songs[0].singer[0].mid}.jpg`,
                        songNum: result.data.song.totalnum, // Total songs found in search
                        albumNum: '-',
                        mvNum: '-'
                    };
                }
            }

            if (singerData) {
                updateSingerInfo(singerData);
            }

            if (songs.length > 0) {
                // Fetch stats for these songs (collect count)
                await fetchAndRenderSongs(songs);
            } else {
                songListEl.innerHTML = '<div class="loading">未找到歌曲</div>';
            }

        } else {
            songListEl.innerHTML = '<div class="loading">未找到相关数据</div>';
        }
    } catch (error) {
        console.error('Error:', error);
        songListEl.innerHTML = '<div class="loading">加载失败，请重试</div>';
    }
}

function updateSingerInfo(data) {
    document.getElementById('singer-title').textContent = data.singerName;
    if (data.singerPic) {
        // Use a higher resolution image if possible, or the one provided
        // QQ Music singer images: T001R150x150M000... -> T001R500x500M000...
        const bigPic = data.singerPic.replace('150x150', '500x500');
        document.getElementById('singer-bg').style.backgroundImage = `url('${bigPic}')`;
    }

    document.getElementById('total-songs').textContent = data.songNum || '-';
    document.getElementById('total-albums').textContent = data.albumNum || '-';
    document.getElementById('total-mvs').textContent = data.mvNum || '-';
}

async function fetchAndRenderSongs(songs) {
    const songListEl = document.getElementById('song-list');
    
    // Get list of song mids to fetch stats
    const mids = songs.map(s => s.songMID || s.songmid).filter(id => id).slice(0, 10); // Limit to 10 for batch
    
    let statsMap = {};
    let totalCollects = 0;

    try {
        const statsRes = await fetch(`/api/song_stats?songmids=${mids.join(',')}`);
        const statsData = await statsRes.json();
        
        if (statsData.code === 0 && statsData.song_stats && statsData.song_stats.data) {
             const list = statsData.song_stats.data.song_visit_info || statsData.song_stats.data.list || [];
             list.forEach(item => {
                 // The key might be song_mid or just mid inside the object
                 // QQ Music structure varies. Usually it returns a map or list.
                 // Let's assume list with song_mid
                 const mid = item.song_mid || item.mid;
                 const count = item.collect_count || 0;
                 statsMap[mid] = count;
                 totalCollects += count;
             });
        }
    } catch (e) {
        console.warn("Failed to fetch detailed stats", e);
    }

    // Update Total Collects Display
    document.getElementById('total-collects').textContent = formatNumber(totalCollects) + '+';

    // Render List
    songListEl.innerHTML = '';
    songs.forEach((song, index) => {
        const mid = song.songMID || song.songmid;
        const songName = song.songName || song.songname;
        const albumName = song.albumName || song.albumname;
        const collectCount = statsMap[mid] || 0;
        
        // Fake "Listening Now" based on collect count ratio (just for visual simulation of the screenshot)
        // In reality, we don't have this data.
        const listeningNow = Math.floor(collectCount / 200) + Math.floor(Math.random() * 50);

        const div = document.createElement('div');
        div.className = 'song-item';
        div.innerHTML = `
            <div class="song-main">
                <div class="song-title ${index < 3 ? 'active' : ''}">${index + 1}. ${escapeHtml(songName)}</div>
                <div class="song-meta">${escapeHtml(albumName)}</div>
            </div>
            <div class="song-stat">
                <div class="stat-row" title="总收藏量">
                    <i>❤️</i>
                    <span class="stat-num pink">${formatNumber(collectCount)}</span>
                </div>
            </div>
            <div class="song-stat">
                <div class="stat-row" title="当前模拟热度">
                    <i>🔥</i>
                    <span class="stat-num blue">${formatNumber(listeningNow)}</span>
                </div>
            </div>
        `;
        songListEl.appendChild(div);
    });
}

function formatNumber(num) {
    if (!num) return '0';
    if (num > 100000000) {
        return (num / 100000000).toFixed(2) + '亿';
    }
    if (num > 10000) {
        return (num / 10000).toFixed(1) + 'w';
    }
    return num.toString();
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
