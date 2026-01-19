let upcomingTours = [];

async function fetchTours() {
  try {
    const response = await fetch("/api/upcoming-tours");
    if (response.ok) {
      const data = await response.json();
      if (data && data.length > 0) {
        upcomingTours = data;
        renderTourSlider(); // 只有拿到数据才渲染
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
      station.innerText = `${tour.city}站`;
      
      const countdown = document.createElement("div");
      countdown.className = "countdown";
      countdown.id = `countdown-${index}`; // 给个ID方便更新
      countdown.dataset.date = tour.date;  // 存下日期方便计算
      
      const venue = document.createElement("div");
      venue.className = "venue-name";
      venue.innerText = tour.venue;
      
      card.appendChild(station);
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
    
    if (diff <= 0) {
      // 演出已开始或结束
      const isSameDay = now.toDateString() === targetDate.toDateString();
      
      if (isSameDay) {
        el.innerText = "TODAY!";
        el.style.color = "#ff69b4"; // 亮粉色强调
        el.style.fontWeight = "bold";
      } else {
        // 演出已过，移除该卡片
        const card = el.closest('.tour-card');
        if (card) {
          card.remove();
          // 刷新按钮状态
          setTimeout(updateNavButtons, 100);
        }
        return;
      }
    } else {
      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);
      
      if (days > 0) {
        // 大于一天显示天数
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
  // 移动端 Touch 监听（保留移动端的交互，或者也可以考虑统一去掉）
  // 既然用户要求“固定圆心”，可能移动端也不需要拖来拖去了。
  // 但为了保留一点趣味性，移动端可以暂时保留“点击显示洞”的效果，位置也可以固定。
  
  // 简化：移动端点击时，也在中心显示洞
  // 如果需要完全移除 JS 交互，CSS 里的 :hover 在移动端体验不佳（需要点击触发）
  // 这里暂时保留一个简单的 Touch 触发器，只控制 radius
  
  mainCard.addEventListener('touchstart', () => {
    mainCard.style.setProperty('--hole-radius', '80px');
  }, { passive: true });
  
  mainCard.addEventListener('touchend', () => {
    mainCard.style.setProperty('--hole-radius', '0px');
  });
}
