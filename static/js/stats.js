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
    
    // Event listeners for Lyrics Modal
    document.getElementById('close-lyrics').addEventListener('click', () => {
        document.getElementById('lyrics-modal').style.display = 'none';
    });
    
    // Close modal when clicking outside
    document.getElementById('lyrics-modal').addEventListener('click', (e) => {
        if (e.target.id === 'lyrics-modal') {
            document.getElementById('lyrics-modal').style.display = 'none';
        }
    });

    // Event listener for Back to Hot Songs
    document.getElementById('back-to-hot-btn').addEventListener('click', () => {
        if (originalHotSongs.length > 0) {
            renderSongs(originalHotSongs, {});
            document.getElementById('song-list-title').textContent = '热门歌曲';
            document.getElementById('back-to-hot-btn').style.display = 'none';
        }
    });
});

let originalHotSongs = [];

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
                    pic: z.singerPic,
                    // 补充更多字段
                    albumNum: z.albumNum,
                    mvNum: z.mvNum,
                    songNum: z.songNum
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
            // 保存原始热门歌曲列表
            originalHotSongs = songs;
            
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
    
    // 如果有简介信息，可以在这里显示
    // 目前搜索接口返回的简介较少，这里可以放一些静态文案或者基于统计数据的生成文案
    const descEl = document.getElementById('singer-desc');
    if (descEl) {
        if (singer.songNum) {
            descEl.style.display = 'block';
            descEl.innerHTML = `
                ${singer.name}，收录歌曲 <b>${singer.songNum}</b> 首，
                专辑 <b>${singer.albumNum}</b> 张，
                MV <b>${singer.mvNum}</b> 个。<br>
                数据实时同步自 QQ 音乐。
            `;
        } else {
            descEl.style.display = 'none';
        }
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
        // 兼容不同的数据结构：
        // 1. song.album.mid (嵌套结构)
        // 2. song.albummid (扁平结构)
        const mid = song.album?.mid || song.albummid || song.albumMid;
        const name = song.album?.name || song.albumname || song.albumName;
        
        // 确保有 mid 和 name，且不是空的
        if (mid && name) {
            if (!albumMap.has(mid)) {
                // 尝试获取发布时间
                // 优先顺序: album.time_public -> song.time_public -> song.pubtime -> album.pub_time
                let time = '';
                if (song.album && song.album.time_public) time = song.album.time_public;
                else if (song.time_public) time = song.time_public;
                else if (song.pubtime) time = song.pubtime;
                else if (song.pub_time) time = song.pub_time;
                
                albumMap.set(mid, {
                    mid: mid,
                    name: name,
                    time_public: time
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

    // 按发布时间倒序排序 (如果有时间的话)
    albums.sort((a, b) => {
        const timeA = parseTime(a.time_public);
        const timeB = parseTime(b.time_public);
        return timeB - timeA;
    });

    albumListEl.innerHTML = '';
    albums.forEach(album => {
        const div = document.createElement('div');
        div.className = 'album-item';
        
        // 封面图
        const picUrl = `https://y.gtimg.cn/music/photo_new/T002R300x300M000${album.mid}.jpg`;
        
        // 格式化时间
        let pubTime = formatPubTime(album.time_public);

        div.onclick = () => fetchAlbumSongs(album.mid, album.name);

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

async function fetchAlbumSongs(mid, albumName) {
    const songListEl = document.getElementById('song-list');
    songListEl.innerHTML = '<div class="loading">正在加载专辑歌曲...</div>';
    
    // Show back button
    document.getElementById('song-list-title').textContent = `专辑: ${albumName}`;
    document.getElementById('back-to-hot-btn').style.display = 'block';

    try {
        const response = await fetch(`/api/album_songs?mid=${mid}`);
        const result = await response.json();
        
        if (result.code === 0 && result.data && result.data.list) {
            // Inject album date if missing in songs (common in album detail API)
            const albumDate = result.data.aDate || result.data.pub_time || '';
            if (albumDate) {
                result.data.list.forEach(song => {
                    // Inject into a property that renderSongs looks for
                    if (!song.time_public && !song.pubtime && !song.pub_time) {
                        song.time_public = albumDate;
                    }
                });
            }
            renderSongs(result.data.list, {});
        } else {
            songListEl.innerHTML = '<div class="loading">暂无歌曲数据</div>';
        }
    } catch (e) {
        console.error(e);
        songListEl.innerHTML = '<div class="loading">加载失败</div>';
    }
}

// 辅助函数：统一解析时间用于排序
function parseTime(timeStr) {
    if (!timeStr) return 0;
    // 如果是时间戳 (数字或字符串)
    if (/^\d+$/.test(timeStr)) {
        let ts = parseInt(timeStr);
        if (String(ts).length === 10) ts *= 1000;
        return ts;
    }
    // 如果是日期字符串 YYYY-MM-DD
    const d = new Date(timeStr);
    return isNaN(d.getTime()) ? 0 : d.getTime();
}

// 辅助函数：统一格式化显示时间
function formatPubTime(timeStr) {
    if (!timeStr) return '-';
    
    // 如果是时间戳
    if (/^\d+$/.test(timeStr)) {
         let ts = parseInt(timeStr);
         if (String(ts).length === 10) ts *= 1000;
         const date = new Date(ts);
         if (!isNaN(date.getTime())) {
             return date.getFullYear() + '-' + (date.getMonth() + 1).toString().padStart(2, '0') + '-' + date.getDate().toString().padStart(2, '0');
         }
    }
    return timeStr; // 原样返回（如果是 YYYY-MM-DD 格式）
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

        // 获取 songmid
        const songmid = song.songmid || song.mid;
        const singerName = (song.singer && song.singer.length > 0) ? song.singer[0].name : "杨丞琳";

        // Add click event for lyrics
        div.onclick = () => fetchLyrics(songmid, songName, singerName);

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

async function fetchLyrics(mid, songName, singerName) {
    const modal = document.getElementById('lyrics-modal');
    const titleEl = document.getElementById('lyrics-title');
    const metaEl = document.getElementById('lyrics-meta');
    const contentEl = document.getElementById('lyrics-content');
    
    // Show modal with loading state
    modal.style.display = 'flex';
    titleEl.textContent = songName;
    metaEl.innerHTML = '';
    contentEl.textContent = '正在加载歌词...';
    
    try {
        const response = await fetch(`/api/lyrics?mid=${mid}`);
        const data = await response.json();
        
        if (data.lyric) {
            // Parse lyrics
            const rawLyric = data.lyric;
            const lines = rawLyric.split('\n');
            let lyricText = '';
            let composer = '';
            let lyricist = '';
            
            // Regex for parsing metadata
            const tiReg = /\[ti:(.*?)\]/;
            const arReg = /\[ar:(.*?)\]/;
            const alReg = /\[al:(.*?)\]/;
            const byReg = /\[by:(.*?)\]/;
            const offsetReg = /\[offset:(.*?)\]/;
            
            // Regex for timestamp
            const timeReg = /\[\d{2}:\d{2}\.\d{2,3}\]/g;
            
            lines.forEach(line => {
                // Check for metadata lines (often in the first few lines without timestamp or with 00:00)
                if (line.includes('词：')) lyricist = line.replace(/.*词：/, '').replace(/\]/, '').trim();
                if (line.includes('曲：')) composer = line.replace(/.*曲：/, '').replace(/\]/, '').trim();
                
                // Clean lyrics
                let cleanLine = line
                    .replace(timeReg, '')
                    .replace(tiReg, '')
                    .replace(arReg, '')
                    .replace(alReg, '')
                    .replace(byReg, '')
                    .replace(offsetReg, '')
                    .trim();
                    
                if (cleanLine) {
                    lyricText += cleanLine + '\n';
                }
            });
            
            // Build meta info
            let metaHtml = '';
            if (lyricist) metaHtml += `作词：${lyricist} `;
            if (composer) metaHtml += `作曲：${composer}`;
            
            metaEl.innerHTML = metaHtml || `${singerName}`;
            contentEl.textContent = lyricText || '暂无歌词文本';
        } else {
            contentEl.textContent = '未找到歌词';
        }
    } catch (e) {
        console.error(e);
        contentEl.textContent = '歌词加载失败';
    }
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
