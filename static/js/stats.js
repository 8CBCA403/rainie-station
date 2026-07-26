document.addEventListener('DOMContentLoaded', () => {
    // 搜索框已被注释掉，所以加个判断
    const searchBtn = document.getElementById('search-btn');
    const searchInput = document.getElementById('singer-name');

    if (searchBtn && searchInput) {
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
    }

    // Event listener for Back to Hot Songs
    const backBtn = document.getElementById('back-to-hot-btn');
    if (backBtn) {
        backBtn.addEventListener('click', () => {
            if (originalHotSongs.length > 0) {
                renderSongs(originalHotSongs, {});
                document.getElementById('song-list-title').textContent = '热门歌曲';
                backBtn.style.display = 'none';
            }
        });
    }

    // Event listeners for Lyrics Modal
    const closeLyrics = document.getElementById('close-lyrics');
    if (closeLyrics) {
        closeLyrics.addEventListener('click', () => {
            document.getElementById('lyrics-modal').style.display = 'none';
        });
    }

    // Close modal when clicking outside
    const lyricsModal = document.getElementById('lyrics-modal');
    if (lyricsModal) {
        lyricsModal.addEventListener('click', (e) => {
            if (e.target.id === 'lyrics-modal') {
                lyricsModal.style.display = 'none';
            }
        });
    }

    // Initial load
    searchSinger("杨丞琳");
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
        let isFallbackMode = false;
        let skipIndexFetch = false;

        // QQ Music 官方结构
        if (result.code === 0 && result.data) {
            const d = result.data;
            isFallbackMode = !!d._fallback;
            skipIndexFetch = !!d._skip_index || isFallbackMode;

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

    // 注意：不再调用 updateSingerInfo 覆盖简介区域
    // 只更新头像和名字，不更新 stats.html 中写死的 HTML 简介
    if (singerData) {
        document.getElementById('singer-title').textContent = singerData.name;
        if (singerData.pic) {
            const picUrl = singerData.pic.replace('150x150', '500x500').replace('300x300', '800x800');
            document.getElementById('singer-bg').style.backgroundImage = `url('${picUrl}')`;
        }
    }

    // 渲染歌曲列表
    renderSongs(songs, {}, { skipIndexFetch, isFallbackMode });

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
    /*
    // 禁用 JS 对简介区域的修改，保持 HTML 静态内容
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
    */
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

function renderSongs(songs, statsMap, options = {}) {
    const songListEl = document.getElementById('song-list');
    songListEl.innerHTML = '';

    // 初始化进度条
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const progressPercent = document.getElementById('progress-percent');

    if (progressContainer) {
        progressContainer.style.display = 'block';
        progressBar.style.width = '0%';
        progressPercent.textContent = '0%';
        progressText.textContent = `准备分析 ${songs.length} 首歌曲...`;
    }

    let completedCount = 0;
    const totalCount = songs.length;

    // 进度更新函数
    const updateProgress = () => {
        completedCount++;
        const percent = Math.round((completedCount / totalCount) * 100);
        if (progressBar) progressBar.style.width = `${percent}%`;
        if (progressPercent) progressPercent.textContent = `${percent}%`;
        if (progressText) progressText.textContent = `正在分析: ${completedCount}/${totalCount}`;

        if (completedCount >= totalCount) {
            setTimeout(() => {
                if (progressText) progressText.textContent = '分析完成';
                // 3秒后淡出进度条
                setTimeout(() => {
                    if (progressContainer) progressContainer.style.display = 'none';
                }, 3000);
            }, 500);
        }
    };

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
            <!-- 1. 左侧：歌曲基础信息 -->
            <div class="song-info-col">
                <div class="song-title ${index < 3 ? 'active' : ''}">
                    <span style="opacity:0.5; margin-right:8px; font-size:0.9em;">#${index + 1}</span>
                    ${escapeHtml(songName)}
                </div>
                <div class="song-album">
                    💿 ${escapeHtml(albumName)}
                    <span style="opacity:0.4; margin:0 5px;">|</span>
                    📅 ${escapeHtml(pubTime.toString().includes('-') ? pubTime : (pubTime == '-' ? '-' : new Date(pubTime).getFullYear()))}
                </div>
            </div>

            <!-- 2. 中间：核心指数数据 -->
            <div class="song-index-col" id="index-data-${songmid}">
                <div style="display:flex; align-items:center; gap:8px;">
                    <div class="loading-spinner"></div>
                    <span style="opacity:0.5; font-size:0.85rem;">等待队列中...</span>
                </div>
            </div>

            <!-- 3. 右侧：走势图与成就 -->
            <div class="song-chart-col" id="index-chart-${songmid}">
                <!-- 预留给图表 -->
            </div>
        `;
        songListEl.appendChild(div);
    });

    if (options.skipIndexFetch) {
        if (progressContainer) progressContainer.style.display = 'none';
        songs.forEach(song => {
            const songmid = song.songmid || song.mid;
            const dataEl = document.getElementById(`index-data-${songmid}`);
            const chartEl = document.getElementById(`index-chart-${songmid}`);
            if (dataEl) {
                dataEl.innerHTML = options.isFallbackMode
                    ? '<span style="opacity:0.5; font-size:0.85rem;">本地备用曲库：仅展示基础歌曲信息</span>'
                    : '<span style="opacity:0.5; font-size:0.85rem;">在线曲库：实时指数暂不提供</span>';
            }
            if (chartEl) {
                chartEl.innerHTML = '<div style="opacity:0.35; font-size:0.8rem;">暂无实时趋势</div>';
            }
        });
        return;
    }

    // === 并发控制 ===
    // 服务器性能较弱 (2核2G)，必须限制并发为 1，否则 5 个浏览器实例会撑爆内存
    const CONCURRENT_LIMIT = 1;
    processQueue(songs, CONCURRENT_LIMIT);
}

// 带并发限制的队列处理
async function processQueue(songs, limit) {
    const songListEl = document.getElementById('song-list');

    // 初始化进度
    const progressText = document.getElementById('progress-text');
    const progressBar = document.getElementById('progress-bar');
    const progressPercent = document.getElementById('progress-percent');

    let completedCount = 0;
    const totalCount = songs.length;
    let activeCount = 0;
    let index = 0;

    const next = () => {
        if (index >= totalCount) return;

        const song = songs[index];
        const currentIndex = index;
        index++;
        activeCount++;

        const songmid = song.songmid || song.mid;

        // 更新 UI 状态
        const statusEl = document.getElementById(`index-data-${songmid}`)?.querySelector('span');
        if (statusEl) statusEl.textContent = '正在分析...';

        // 执行请求
        fetchSongIndex(songmid, {
            dataContainer: document.getElementById(`index-data-${songmid}`),
            chartContainer: document.getElementById(`index-chart-${songmid}`)
        }).finally(() => {
            activeCount--;
            completedCount++;

            // 更新进度条
            const percent = Math.round((completedCount / totalCount) * 100);
            if (progressBar) progressBar.style.width = `${percent}%`;
            if (progressPercent) progressPercent.textContent = `${percent}%`;
            if (progressText) progressText.textContent = `正在分析: ${completedCount}/${totalCount}`;

            // 继续处理下一个
            if (index < totalCount) {
                next();
            } else if (activeCount === 0) {
                // 全部完成
                if (progressText) progressText.textContent = '所有歌曲分析完成';
                setTimeout(() => {
                    const container = document.getElementById('progress-container');
                    if (container) container.style.display = 'none';
                }, 3000);
            }
        });
    };

    // 启动初始批次
    for (let i = 0; i < Math.min(limit, totalCount); i++) {
        next();
    }
}

// 简单的 Loading CSS
const style = document.createElement('style');
style.innerHTML = `
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
.loading-spinner {
    width: 16px; height: 16px;
    border: 2px solid rgba(255,255,255,0.1);
    border-top: 2px solid #4facfe;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}
`;
document.head.appendChild(style);

async function fetchSongIndex(mid, containers) {
    if (!containers.dataContainer) return;

    try {
        const response = await fetch(`/api/song_index?mid=${mid}`);
        const result = await response.json();

        // 成功获取数据后，将数据绑定到 DOM 元素上，供弹窗使用
        if (result.code === 0 && result.data) {
            const d = result.data;

            // 绑定数据到行元素 (song-item)
            // 往上找父级 .song-item
            const songItem = containers.dataContainer.closest('.song-item');
            if (songItem) {
                // 将成就数据转为 JSON 字符串存入 dataset
                songItem.dataset.achievements = JSON.stringify(d.achievements || []);
            }

            // --- 渲染中间列：核心数据 ---
            // 颜色判断辅助函数
            const getChangeColor = (text) => {
                if (!text) return '#fff';
                if (text.includes('下降') || text.includes('-')) return '#20bf64'; // 绿色代表下降
                if (text.includes('上升') || text.includes('+')) return '#ff5f5f'; // 红色代表上升
                return '#aaa'; // 无变化
            };

            containers.dataContainer.innerHTML = `
                <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <div>
                        <div style="color:#20bf64; font-size:1.4rem; font-weight:bold; line-height:1;">${d.music_index || '-'}</div>
                        <div style="font-size:0.75rem; opacity:0.6; margin-top:2px;">
                            实时音乐指数
                            <span style="opacity:0.5; margin-left:5px; font-size:0.65rem;">${d.update_time || ''}</span>
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="color:#ffb6c1; font-size:1.4rem; font-weight:bold; line-height:1;">#${d.global_rank || '-'}</div>
                        <div style="font-size:0.75rem; opacity:0.6; margin-top:2px;">全站排名</div>
                    </div>
                </div>

                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; background:rgba(255,255,255,0.03); padding:8px; border-radius:6px;">
                    <div style="text-align:center;">
                        <div style="font-size:0.9rem;">${d.yesterday_index || '-'}</div>
                        <div style="font-size:0.7rem; color:${getChangeColor(d.index_change)}">
                            ${d.index_change || '-'}
                        </div>
                        <div style="font-size:0.65rem; opacity:0.4;">昨日指数</div>
                    </div>
                    <div style="text-align:center; border-left:1px solid rgba(255,255,255,0.1);">
                        <div style="font-size:0.9rem;">${d.yesterday_rank || '-'}</div>
                        <div style="font-size:0.7rem; color:${getChangeColor(d.rank_change)}">
                            ${d.rank_change || '-'}
                        </div>
                        <div style="font-size:0.65rem; opacity:0.4;">昨日排名</div>
                    </div>
                </div>
            `;

            // --- 渲染右侧列：走势图与成就 ---
            let chartHtml = '';
            if (d.chart_image) {
                chartHtml = `
                    <div style="flex:1; display:flex; justify-content:center; align-items:center; width:100%;">
                        <img src="${d.chart_image}"
                             style="max-height:120px; width:auto; max-width:100%; border-radius:6px; opacity:0.95; box-shadow:0 4px 12px rgba(0,0,0,0.3); cursor: zoom-in;"
                             alt="走势图"
                             onclick="showLightbox(this.src); event.stopPropagation();">
                    </div>
                `;
            } else {
                chartHtml = `<div style="flex:1; display:flex; align-items:center; justify-content:center; opacity:0.3; font-size:0.8rem;">暂无走势图</div>`;
            }

            // 链接按钮
            const linkBtn = `
                <a href="https://y.qq.com/m/client/music_index/index.html?ADTAG=cbshare&channelId=10036163&mid=${mid}&type=${mid}"
                   target="_blank"
                   style="position:absolute; top:0; right:0; padding:4px 8px; background:rgba(255,255,255,0.1); border-radius:0 0 0 8px; color:#4facfe; font-size:0.7rem; text-decoration:none;">
                   🔗 源站
                </a>
            `;

            // 容器设为相对定位以便放链接
            containers.chartContainer.style.position = 'relative';
            containers.chartContainer.innerHTML = chartHtml + linkBtn;

        } else {
            containers.dataContainer.innerHTML = '<span style="opacity:0.3">数据获取失败</span>';
            containers.chartContainer.innerHTML = '';
        }
    } catch (e) {
        console.error(e);
        containers.dataContainer.innerHTML = '<span style="opacity:0.3">请求超时</span>';
    }
}

async function fetchLyrics(mid, songName, singerName) {
    const modal = document.getElementById('lyrics-modal');
    const titleEl = document.getElementById('lyrics-title');
    const contentEl = document.getElementById('lyrics-content');
    const metaEl = document.getElementById('lyrics-meta');
    const achListEl = document.getElementById('achievements-list'); // 新增：成就列表容器

    // 1. 初始化弹窗状态
    modal.style.display = 'flex';
    titleEl.textContent = songName;
    metaEl.textContent = `歌手：${singerName}`;
    contentEl.textContent = '正在加载歌词...';
    achListEl.innerHTML = '<div style="text-align:center; margin-top:50px; opacity:0.5;">正在加载成就...</div>'; // Loading 状态

    // 2. 获取数据
    // 尝试从 DOM 获取缓存的成就数据
    const songItem = document.getElementById(`index-data-${mid}`)?.closest('.song-item');
    let cachedAchs = null;
    if (songItem && songItem.dataset.achievements) {
        try {
            cachedAchs = JSON.parse(songItem.dataset.achievements);
        } catch (e) { console.error('解析缓存成就失败', e); }
    }

    // 如果有缓存，直接显示成就，不再请求 song_index
    if (cachedAchs) {
        renderAchievements(cachedAchs, achListEl);
        // 只请求歌词
        fetch(`/api/lyrics?mid=${mid}`)
            .then(res => res.json())
            .then(data => renderLyrics(data, contentEl))
            .catch(() => contentEl.textContent = '歌词加载失败');
    } else {
        // 没有缓存，并行请求
        try {
            const [lyricsRes, indexRes] = await Promise.all([
                fetch(`/api/lyrics?mid=${mid}`),
                fetch(`/api/song_index?mid=${mid}`)
            ]);

            const lyricsData = await lyricsRes.json();
            renderLyrics(lyricsData, contentEl);

            const indexData = await indexRes.json();
            if (indexData.code === 0 && indexData.data) {
                renderAchievements(indexData.data.achievements, achListEl);
            } else {
                achListEl.innerHTML = '<div style="text-align:center; margin-top:50px; opacity:0.5;">暂无成就数据</div>';
            }
        } catch (e) {
            console.error(e);
            contentEl.textContent = '加载失败';
            achListEl.innerHTML = '<div style="text-align:center; margin-top:50px; opacity:0.5;">加载失败</div>';
        }
    }
}

// 辅助函数：渲染歌词
function renderLyrics(data, container) {
    const metaEl = document.getElementById('lyrics-meta');

    if (data.lyric || data.lyrics) {
        // 兼容不同的字段名 (API 可能返回 lyric 或 lyrics)
        const rawLyric = data.lyric || data.lyrics;

        // 解析歌词
        const lines = rawLyric.split('\n');
        let lyricText = '';
        let composer = '';
        let lyricist = '';

        // 正则表达式
        const tiReg = /\[ti:(.*?)\]/;
        const arReg = /\[ar:(.*?)\]/;
        const alReg = /\[al:(.*?)\]/;
        const byReg = /\[by:(.*?)\]/;
        const offsetReg = /\[offset:(.*?)\]/;
        const timeReg = /\[\d{2}:\d{2}\.\d{2,3}\]/g;

        lines.forEach(line => {
            // 提取元数据
            if (line.includes('词：') || line.includes('作词')) {
                lyricist = line.replace(/.*(词|作词)：/, '').replace(/\]/, '').trim();
            }
            if (line.includes('曲：') || line.includes('作曲')) {
                composer = line.replace(/.*(曲|作曲)：/, '').replace(/\]/, '').trim();
            }

            // 清洗歌词内容
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

        // 渲染元数据
        let metaHtml = '';
        if (lyricist) metaHtml += `<span>📝 作词：${lyricist}</span> `;
        if (composer) metaHtml += `<span style="margin-left:15px;">🎵 作曲：${composer}</span>`;
        metaEl.innerHTML = metaHtml;

        // 渲染歌词文本
        container.textContent = lyricText || '暂无歌词文本';

        // 如果有翻译
        if (data.trans) {
            container.textContent += '\n\n=== 翻译 ===\n\n' + data.trans;
        }
    } else {
        container.textContent = '暂无歌词';
        metaEl.innerHTML = '';
    }
}

// 辅助函数：渲染成就
function renderAchievements(achs, container) {
    if (achs && achs.length > 0) {
        container.innerHTML = achs.map(ach => {
            const match = ach.match(/^(\d{4}\/\d{2}\/\d{2})\s+(.+)/);
            const date = match ? match[1] : '';
            const content = match ? match[2] : ach;
            return `
                <div class="ach-item">
                    ${date ? `<div class="ach-date">${date}</div>` : ''}
                    <div class="ach-content">${escapeHtml(content)}</div>
                </div>
            `;
        }).join('');
    } else {
        container.innerHTML = '<div style="text-align:center; margin-top:50px; opacity:0.5;">暂无近期成就</div>';
    }
}

// Lightbox 显示函数
function showLightbox(src) {
    const modal = document.getElementById('lightbox-modal');
    const img = document.getElementById('lightbox-img');
    if (modal && img) {
        img.src = src;
        modal.style.display = 'flex';
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
