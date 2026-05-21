document.addEventListener('DOMContentLoaded', async () => {
  const container = document.getElementById('digest-container');
  const paginationContainer = document.getElementById('pagination-container');
  
  let allData = [];
  let currentPage = 1;
  const itemsPerPage = 10;
  
  try {
    const response = await fetch('./data.json');
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    allData = await response.json();
    
    if (allData.length === 0) {
      container.innerHTML = '<p class="loader">目前還沒有任何分析紀錄。</p>';
      return;
    }
    
    renderPage(1);
    
  } catch (error) {
    console.error('Failed to fetch digest data:', error);
    container.innerHTML = `<p class="loader" style="color: #ef4444;">讀取資料失敗：請確認 history.json 已正確生成並放到 public/data.json</p>`;
  }

  function renderPage(page) {
    currentPage = page;
    container.innerHTML = ''; // 清除目前內容
    
    const startIndex = (page - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageData = allData.slice(startIndex, endIndex);
    
    pageData.forEach(item => {
      const card = document.createElement('div');
      card.className = 'card';
      
      const header = document.createElement('div');
      header.className = 'card-header';
      
      const title = document.createElement('h2');
      title.className = 'card-title';
      title.innerHTML = `<a href="${item.url}" target="_blank" rel="noopener noreferrer">${item.title}</a>`;
      
      // 檢查是否為 7 天內的新文章
      const itemDate = new Date(item.date.replace(' ', 'T'));
      const now = new Date();
      const diffTime = Math.abs(now - itemDate);
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      
      if (diffDays <= 7) {
        const badge = document.createElement('span');
        badge.className = 'badge-new';
        badge.textContent = 'NEW';
        title.appendChild(badge);
      }
      
      const date = document.createElement('span');
      date.className = 'card-date';
      date.textContent = item.date;
      
      header.appendChild(title);
      header.appendChild(date);
      
      // Expand / Collapse Wrapper
      const wrapper = document.createElement('div');
      wrapper.className = 'card-content-wrapper collapsed';
      
      const body = document.createElement('div');
      body.className = 'card-body';
      if (typeof marked !== 'undefined') {
        body.innerHTML = marked.parse(item.digest);
      } else {
        body.textContent = item.digest;
      }
      
      wrapper.appendChild(body);
      
      const readMoreContainer = document.createElement('div');
      readMoreContainer.className = 'read-more-container';
      const readMoreBtn = document.createElement('button');
      readMoreBtn.className = 'read-more-btn';
      readMoreBtn.textContent = '繼續瀏覽';
      
      readMoreBtn.addEventListener('click', () => {
        if (wrapper.classList.contains('collapsed')) {
          wrapper.classList.remove('collapsed');
          readMoreBtn.textContent = '收起內容';
        } else {
          wrapper.classList.add('collapsed');
          readMoreBtn.textContent = '繼續瀏覽';
        }
      });
      
      readMoreContainer.appendChild(readMoreBtn);
      
      card.appendChild(header);
      card.appendChild(wrapper);
      card.appendChild(readMoreContainer);
      
      container.appendChild(card);
    });
    
    renderPaginationControls();
    
    // 捲動回頂部
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function renderPaginationControls() {
    paginationContainer.innerHTML = '';
    const totalPages = Math.ceil(allData.length / itemsPerPage);
    
    if (totalPages <= 1) return;
    
    // 建立「上一頁」
    const prevBtn = document.createElement('button');
    prevBtn.className = 'page-btn';
    prevBtn.innerHTML = '&lt;';
    prevBtn.disabled = currentPage === 1;
    prevBtn.addEventListener('click', () => {
      if (currentPage > 1) renderPage(currentPage - 1);
    });
    paginationContainer.appendChild(prevBtn);
    
    // 建立頁碼
    for (let i = 1; i <= totalPages; i++) {
      const btn = document.createElement('button');
      btn.className = `page-btn ${i === currentPage ? 'active' : ''}`;
      btn.textContent = i;
      btn.addEventListener('click', () => renderPage(i));
      paginationContainer.appendChild(btn);
    }
    
    // 建立「下一頁」
    const nextBtn = document.createElement('button');
    nextBtn.className = 'page-btn';
    nextBtn.innerHTML = '&gt;';
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.addEventListener('click', () => {
      if (currentPage < totalPages) renderPage(currentPage + 1);
    });
    paginationContainer.appendChild(nextBtn);
  }
});
