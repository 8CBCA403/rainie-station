let upcomingTours = [];

async function fetchTours() {
  try {
    const response = await fetch("/api/upcoming-tours");
    if (response.ok) {
      const data = await response.json();
      if (data && data.length > 0) {
        // Filter: Show ALL "房间里的大象" tours (past & future) + ANY other future tours
        const now = new Date().toISOString();
        
        upcomingTours = data.filter(t => {
            // 1. Always show "房间里的大象" (current tour), regardless of date
            if (t.tour_name === "房间里的大象") return true;
            
            // 2. For other tours, only show if future
            return t.date >= now;
        });
        
        // Sort by date ASC
        upcomingTours.sort((a, b) => new Date(a.date) - new Date(b.date));
        
        if (upcomingTours.length > 0) {
            renderTourSlider();
        } else {
            const tourInfoEl = document.getElementById("tour-info");
            if (tourInfoEl) tourInfoEl.style.display = "none";
        }
      } else {
        // 数据为空，可能要隐藏 slider
        const tourInfoEl = document.getElementById("tour-info");
        if (tourInfoEl) tourInfoEl.style.display = "none";
      }
    }
  } catch (error) {
    console.error("Failed to fetch tours:", error);
  }
}

function renderTourSlider() {
  const tourInfoEl = document.getElementById("tour-info");
  const sliderEl = document.getElementById("tour-slider");
  
  // 清空现有内容
  sliderEl.innerHTML = "";
  
  if (upcomingTours.length > 0) {
    tourInfoEl.style.display = "flex";
    
    upcomingTours.forEach((tour, index) => {
      const card = document.createElement("div");
      card.className = "tour-card";
      
      const station = document.createElement("div");
      station.className = "station-name";
      // 后台返回的 city 已经是 "西安" 等中文
      station.innerText = `${tour.city}`; 
      
      const dateEl = document.createElement("div");
      dateEl.className = "tour-date";
      // 格式化日期：2026-02-07T19:00:00 -> 2026.02.07
      const dateObj = new Date(tour.date);
      const dateStr = dateObj.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      }).replace(/\//g, '.');
      dateEl.innerText = dateStr;

      const countdown = document.createElement("div");
      countdown.className = "countdown";
      countdown.id = `countdown-${index}`; // 给个ID方便更新
      countdown.dataset.date = tour.date;  // 存下日期方便计算
      
      const venue = document.createElement("div");
      venue.className = "venue-name";
      venue.innerText = tour.venue;
      
      card.appendChild(station);
      card.appendChild(dateEl);
      card.appendChild(countdown);
      card.appendChild(venue);
      
      sliderEl.appendChild(card);
    });
    
    updateAllCountdowns();

  } else {
    tourInfoEl.style.display = "none";
  }
}

function updateAllCountdowns() {
  const now = new Date();
  
  upcomingTours.forEach((tour, index) => {
    const el = document.getElementById(`countdown-${index}`);
    if (!el) return;
    
    const targetDate = new Date(tour.date);
    const diff = targetDate - now;
    
    // 只显示未来的场次
    // 如果 diff <= 0 (已过期)，直接不处理，保持为空，或者在 renderTourSlider 阶段就过滤掉
    // 现在的逻辑是 renderTourSlider 已经只渲染 upcomingTours (future only)
    // 所以这里的 diff <= 0 理论上只会出现于 "TODAY" 或者用户长时间停留页面导致过期
    
    if (diff <= 0) {
      const isSameDay = now.toDateString() === targetDate.toDateString();
      if (isSameDay) {
          el.innerText = "TODAY!";
          el.style.color = "#FF9500"; 
          el.style.fontWeight = "bold";
      } else {
          // For past tours (like completed "房间里的大象" shows), display COMPLETED stamp
          el.innerText = ""; // Clear text to make room for stamp
          
          const card = el.closest('.tour-card');
          if (card && !card.querySelector('.stamp')) {
            card.classList.add('finished');
            
            const stamp = document.createElement('div');
            stamp.className = 'stamp';
            stamp.innerText = '已结束';
            card.appendChild(stamp);
          }
      }
    } else {
      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);
      
      if (days > 0) {
        // 大于一天显示天数
        // "19 DAYS LEFT" -> "还有 19 天"
      // 用户要求倒计时用英文： "19 DAYS LEFT"
      const dayLabel = days === 1 ? "DAY" : "DAYS";
      el.innerText = `${days} ${dayLabel} LEFT`; 
      } else {
        // 小于一天显示时分秒倒计时
        el.innerText = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
      }
    }
  });
}

function updateTime() {
  const now = new Date();

  // 更新日期和时间
  const dateStr = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  })
    .format(now)
    .replaceAll("/", ".");

  const timeStr = new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(now);

  document.getElementById("date").innerText = dateStr;
  document.getElementById("clock").innerText = timeStr;

  // 更新所有卡片的倒计时
  updateAllCountdowns();
}

// 页面初始化
updateTime();
fetchTours(); 
setInterval(updateTime, 1000);

// 鼠标滚轮横向滚动支持
const slider = document.getElementById('tour-slider');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');

function updateNavButtons() {
  if (!slider || !prevBtn || !nextBtn) return;
  
  // 永远显示两个箭头（因为支持循环跳转了）
  prevBtn.classList.remove('hidden');
  nextBtn.classList.remove('hidden');
}

if (slider) {
  // 监听滚动更新按钮状态
  slider.addEventListener('scroll', updateNavButtons);
  
  // 初始化按钮状态
  // 需要延迟一点点，等待布局完成
  setTimeout(updateNavButtons, 100);
  
  // 按钮点击事件
  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      // 如果到了最后一张（或者接近最后），跳回第一张
      if (slider.scrollLeft + slider.clientWidth >= slider.scrollWidth - 10) {
          slider.scrollTo({ left: 0, behavior: 'smooth' });
      } else {
          slider.scrollBy({ left: slider.clientWidth, behavior: 'smooth' });
      }
    });
  }
  
  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      // 如果在第一张，跳到最后一张
      if (slider.scrollLeft <= 10) {
          slider.scrollTo({ left: slider.scrollWidth, behavior: 'smooth' });
      } else {
          slider.scrollBy({ left: -slider.clientWidth, behavior: 'smooth' });
      }
    });
  }
  
  // 保留滚轮支持
  slider.addEventListener('wheel', (evt) => {
    // 只有当内容溢出时才拦截滚动
    if (slider.scrollWidth > slider.clientWidth) {
      evt.preventDefault();
      // 兼容触摸板的横向滚动 (deltaX) 和鼠标滚轮的纵向滚动 (deltaY)
      // 增加滚动速度 (* 1.5) 避免被 scroll-snap 吸附回去
      slider.scrollLeft += (evt.deltaY + evt.deltaX) * 1.5;
    }
  }, { passive: false });
}

const mainCard = document.querySelector('.card');

if (mainCard) {
  // 移动端 Touch 交互：随手指移动圆心
  let isTouching = false;
  
  // 初始化变量，避免未定义
  mainCard.style.setProperty('--touch-x', '50%');
  mainCard.style.setProperty('--touch-y', '20%');
  mainCard.style.setProperty('--hole-radius', '0px');

  mainCard.addEventListener('touchstart', (e) => {
      if (window.innerWidth <= 520) {
          isTouching = true;
          
          // 立即更新位置，防止跳变
          const touch = e.touches[0];
          const rect = mainCard.getBoundingClientRect();
          const x = touch.clientX - rect.left;
          const y = touch.clientY - rect.top;
          const limitY = rect.height * 0.5;
          
          if (y <= limitY) {
            mainCard.style.setProperty('--touch-x', `${x}px`);
            mainCard.style.setProperty('--touch-y', `${y}px`);
            mainCard.style.setProperty('--hole-radius', '75px');
          }
      }
  }, { passive: true });

  mainCard.addEventListener('touchend', () => {
      if (window.innerWidth <= 520) {
          isTouching = false;
          mainCard.style.setProperty('--hole-radius', '0px');
      }
  });

  mainCard.addEventListener('touchmove', (e) => {
    // 只有在手机竖屏模式下才启用这个逻辑
    if (window.innerWidth <= 520 && isTouching) {
      const touch = e.touches[0];
      const rect = mainCard.getBoundingClientRect();
      
      // 计算相对坐标
      const x = touch.clientX - rect.left;
      const y = touch.clientY - rect.top;
      
      // 限制在上半屏 (卡片高度的 50%)
      const limitY = rect.height * 0.5;
      
      if (y <= limitY) {
          // 在上半屏：正常移动
          mainCard.style.setProperty('--touch-x', `${x}px`);
          mainCard.style.setProperty('--touch-y', `${y}px`);
          mainCard.style.setProperty('--hole-radius', '75px'); // 保持显示
      } else {
          // 滑到下半屏：洞立即消失
          mainCard.style.setProperty('--hole-radius', '0px');
      }
    }
  }, { passive: true });
}

// 桌面端鼠标交互：只有在卡片中心半径 150px 范围内才触发分裂效果
if (mainCard && window.matchMedia("(pointer: fine)").matches) {
  document.addEventListener('mousemove', (e) => {
    const rect = mainCard.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    
    // 计算鼠标距离卡片中心的距离
    const dist = Math.sqrt(
      Math.pow(e.clientX - centerX, 2) + 
      Math.pow(e.clientY - centerY, 2)
    );
    
    // 阈值：100px
    if (dist <= 100) {
      mainCard.classList.add('hover-active');
    } else {
      mainCard.classList.remove('hover-active');
    }
  });
}
