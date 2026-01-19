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
    
    // 安全地重置元素内容
    const resetEl = (id) => { const el = document.getElementById(id); if(el) el.textContent = '-'; };
    resetEl('total-songs');
    resetEl('total-albums');
    resetEl('total-mvs');
    // document.getElementById('total-collects').textContent = '-';

    try {
        console.log(`Fetching data for: ${name}`); // Debug Log
        const response = await fetch(`/api/search_singer?name=${encodeURIComponent(name)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('API Result:', result); // Debug Log
        
        let singerData = null;
        let songs = [];
        let stats = {};

        // QQ Music 官方结构
        if (result.code === 0 && result.data) {
            const d = result.data;
            
            // 1. 优先从 zhida 获取歌手统计信息
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
            }

            // 2. 优先从 song.list 获取歌曲列表
            if (d.song && d.song.list && d.song.list.length > 0) {
                songs = d.song.list;
                // 如果之前没拿到歌手信息 (zhida不存在), 尝试从歌曲列表提取
                if (!singerData && songs[0].singer && songs[0].singer.length > 0) {
                    singerData = {
                        name: songs[0].singer[0].name,
                        pic: `https://y.gtimg.cn/music/photo_new/T001R150x150M000${songs[0].singer[0].mid}.jpg`
                    };
                    stats = {
                        song_num: d.song.totalnum
                    };
                }
            } else if (d.zhida && d.zhida.zhida_singer) {
                // 如果 song.list 空但 zhida 有歌 (备用)
                songs = d.zhida.zhida_singer.hotsong || [];
            }
        }

        // 只要拿到歌手信息 OR 歌曲列表，就认为成功
        if (singerData || songs.length > 0) {
            // 如果只有歌曲没有歌手信息（极少见），造一个默认的
            if (!singerData && songs.length > 0) {
                singerData = { name: name, pic: '' }; 
            }
            if (singerData) updateSingerInfo(singerData);
            
            updateStats(stats || {});
            
            // 渲染歌曲列表
            renderSongs(songs, {});
            
            // 提取并渲染专辑列表
            processAndRenderAlbums(songs);

        } else {
            songListEl.innerHTML = '<div class="loading">未找到相关数据</div>';
            document.getElementById('album-list').innerHTML = '<div class="loading">暂无专辑</div>';
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
    const songEl = document.getElementById('total-songs');
    if (songEl) songEl.textContent = stats.song_num || '-';
    
    // 之前 HTML 里删了这个元素，这里必须加判断，否则报错白屏
    const albumEl = document.getElementById('total-albums');
    if (albumEl) albumEl.textContent = stats.album_num || '-';
    
    const mvEl = document.getElementById('total-mvs');
    if (mvEl) mvEl.textContent = stats.mv_num || '-';
}

function processAndRenderAlbums(songs) {
    const albumListEl = document.getElementById('album-list');
    if (!albumListEl) return;
    
    if (!songs || songs.length === 0) {
        albumListEl.innerHTML = '<div class="loading">暂无专辑</div>';
        return;
    }

    // 提取专辑信息并去重
    const albumMap = new Map();
    songs.forEach(song => {
        if (song.album && song.album.mid) {
            if (!albumMap.has(song.album.mid)) {
                albumMap.set(song.album.mid, {
                    mid: song.album.mid,
                    name: song.album.name,
                    // 尝试从歌曲时间获取大概的发布时间，因为 song.album 里通常没有详细时间
                    // 或者如果 song.album 有 time_public 更好
                    time_public: song.album.time_public || song.time_public || song.pubtime || ''
                });
            }
        }
    });

    const albums = Array.from(albumMap.values());
    
    // 渲染
    if (albums.length === 0) {
        albumListEl.innerHTML = '<div class="loading">暂无专辑信息</div>';
        return;
    }

    albumListEl.innerHTML = '';
    albums.forEach(album => {
        const div = document.createElement('div');
        div.className = 'album-item';
        
        // 封面图
        const picUrl = `https://y.gtimg.cn/music/photo_new/T002R300x300M000${album.mid}.jpg`;
        
        // 格式化时间
        let pubTime = album.time_public;
        if (/^\d+$/.test(pubTime)) { // 如果是时间戳
             if (String(pubTime).length === 10) pubTime = pubTime * 1000;
             const date = new Date(parseInt(pubTime));
             if (!isNaN(date.getTime())) {
                 pubTime = date.getFullYear() + '-' + (date.getMonth() + 1).toString().padStart(2, '0') + '-' + date.getDate().toString().padStart(2, '0');
             }
        }

        div.innerHTML = `
            <div class="album-cover" style="background-image: url('${picUrl}')"></div>
            <div class="album-info">
                <div class="album-name" title="${escapeHtml(album.name)}">${escapeHtml(album.name)}</div>
                <div class="album-date">${escapeHtml(pubTime)}</div>
            </div>
        `;
        albumListEl.appendChild(div);
    });
}

async function fetchRealCollectCounts(songs) {
    const songListEl = document.getElementById('song-list');
    
    // 如果没有歌，直接返回
    if (!songs || songs.length === 0) {
        songListEl.innerHTML = '<div class="loading">未找到歌曲</div>';
        return;
    }

    // 直接渲染列表（不获取收藏量，只显示基础信息）
    renderSongs(songs, {});
}

function renderSongs(songs, statsMap) {
    const songListEl = document.getElementById('song-list');
    songListEl.innerHTML = '';
    
    songs.forEach((song, index) => {
        const div = document.createElement('div');
        div.className = 'song-item';
        
        const songName = song.songname || song.name || song.songName;
        const albumName = song.albumname || song.album?.name || song.albumName || '';
        // 使用真实的发布时间，如果没有则显示横杠
        // 兼容字段: pubtime (时间戳), time_public (日期字符串)
        let pubTime = song.pubtime || song.time_public || song.pub_time || (song.album ? song.album.time_public : '-') || '-';

        // 3. 时间格式化：支持时间戳转换
        if (/^\d+$/.test(pubTime)) {
            // 如果是 10 位时间戳 (秒)，转毫秒
            if (String(pubTime).length === 10) {
                 pubTime = pubTime * 1000;
            }
            const date = new Date(parseInt(pubTime));
            if (!isNaN(date.getTime())) {
                pubTime = date.getFullYear() + '-' + (date.getMonth() + 1).toString().padStart(2, '0') + '-' + date.getDate().toString().padStart(2, '0');
            }
        }

        div.innerHTML = `
            <div class="song-main">
                <div class="song-title ${index < 3 ? 'active' : ''}">${index + 1}. ${escapeHtml(songName)}</div>
                <div class="song-meta">${escapeHtml(albumName)}</div>
            </div>
            <div class="song-stat" style="min-width: 100px;">
                <div class="stat-row" title="发布时间">
                    <i>📅</i>
                    <span class="stat-num pink" style="font-size: 0.9rem;">${escapeHtml(pubTime)}</span>
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
