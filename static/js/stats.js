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
    songListEl.innerHTML = '<div class="loading">正在获取数据...</div>';
    document.getElementById('total-songs').textContent = '-';
    document.getElementById('total-albums').textContent = '-';
    document.getElementById('total-mvs').textContent = '-';
    document.getElementById('total-collects').textContent = '-';

    try {
        const response = await fetch(`/api/search_singer?name=${encodeURIComponent(name)}`);
        const result = await response.json();
        
        let singerData = null;
        let songs = [];
        let stats = {};

        // 仅处理 QQ Music 官方结构
        if (result.code === 0 && result.data && (result.data.zhida || result.data.song)) {
            const d = result.data;
            if (d.zhida && d.zhida.zhida_singer) {
                const z = d.zhida.zhida_singer;
                singerData = {
                    name: z.singerName,
                    pic: z.singerPic
                };
                stats = {
                    song_num: z.songNum,
                    album_num: z.albumNum,
                    mv_num: z.mvNum
                };
                songs = z.hotsong || [];
            } else if (d.song && d.song.list) {
                songs = d.song.list;
                if (songs.length > 0 && songs[0].singer) {
                    singerData = {
                        name: songs[0].singer[0].name,
                        pic: `https://y.gtimg.cn/music/photo_new/T001R150x150M000${songs[0].singer[0].mid}.jpg`
                    };
                }
                stats = {
                    song_num: d.song.totalnum
                };
            }
        }

        if (singerData) {
            updateSingerInfo(singerData);
            updateStats(stats);
            fetchRealCollectCounts(songs);
        } else {
            songListEl.innerHTML = '<div class="loading">未找到相关数据</div>';
        }

    } catch (error) {
        console.error('Error:', error);
        songListEl.innerHTML = '<div class="loading">加载失败，请重试</div>';
    }
}

function updateSingerInfo(singer) {
    document.getElementById('singer-title').textContent = singer.name;
    if (singer.pic) {
        const picUrl = singer.pic.replace('150x150', '500x500').replace('300x300', '800x800');
        document.getElementById('singer-bg').style.backgroundImage = `url('${picUrl}')`;
    }
}

function updateStats(stats) {
    document.getElementById('total-songs').textContent = stats.song_num || '-';
    document.getElementById('total-albums').textContent = stats.album_num || '-';
    document.getElementById('total-mvs').textContent = stats.mv_num || '-';
    document.getElementById('total-collects').textContent = '-';
}

async function fetchRealCollectCounts(songs) {
    const songListEl = document.getElementById('song-list');
    
    // 如果没有歌，直接返回
    if (!songs || songs.length === 0) {
        songListEl.innerHTML = '<div class="loading">未找到歌曲</div>';
        return;
    }

    // 先渲染列表（显示加载中）
    renderSongs(songs, {});

    // 批量获取收藏量
    const mids = songs.map(s => s.songMID || s.songmid).filter(id => id).slice(0, 10);
    try {
        const statsRes = await fetch(`/api/song_stats?songmids=${mids.join(',')}`);
        const statsData = await statsRes.json();
        
        let statsMap = {};
        let totalCollects = 0;

        if (statsData.code === 0 && statsData.song_stats && statsData.song_stats.data) {
             const list = statsData.song_stats.data.song_visit_info || statsData.song_stats.data.list || [];
             list.forEach(item => {
                 const mid = item.song_mid || item.mid;
                 const count = item.collect_count || 0;
                 statsMap[mid] = count;
                 totalCollects += count;
             });
             
             // 更新总收藏量面板
             document.getElementById('total-collects').innerHTML = 
                `${formatNumber(totalCollects)}+ <div style="font-size:0.6rem;opacity:0.6">Top10 总收藏</div>`;

             // 重新渲染带数据的列表
             renderSongs(songs, statsMap);
        }
    } catch (e) {
        console.warn("Failed to fetch collect stats", e);
    }
}

function renderSongs(songs, statsMap) {
    const songListEl = document.getElementById('song-list');
    songListEl.innerHTML = '';
    
    songs.forEach((song, index) => {
        const div = document.createElement('div');
        div.className = 'song-item';
        
        const songName = song.songname || song.name || song.songName;
        const albumName = song.albumname || song.album?.name || song.albumName || '';
        const mid = song.songMID || song.songmid;
        
        // 收藏量
        const collectCount = statsMap[mid] || 0;
        // 模拟热度 (仅作为视觉展示)
        const heat = Math.floor(collectCount / 200) + Math.floor(Math.random() * 50);

        div.innerHTML = `
            <div class="song-main">
                <div class="song-title ${index < 3 ? 'active' : ''}">${index + 1}. ${escapeHtml(songName)}</div>
                <div class="song-meta">${escapeHtml(albumName)}</div>
            </div>
            <div class="song-stat">
                <div class="stat-row" title="收藏量">
                    <i>❤️</i>
                    <span class="stat-num pink">${formatNumber(collectCount)}</span>
                </div>
            </div>
            <div class="song-stat">
                <div class="stat-row" title="模拟热度">
                    <i>🔥</i>
                    <span class="stat-num blue">${formatNumber(heat)}</span>
                </div>
            </div>
        `;
        songListEl.appendChild(div);
    });
}

function formatNumber(num) {
    if (!num) return '0';
    const n = parseInt(num);
    if (isNaN(n)) return num;
    
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
