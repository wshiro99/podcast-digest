document.addEventListener('DOMContentLoaded', async () => {
  const container = document.getElementById('digest-container');
  
  try {
    const response = await fetch('./data.json');
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    
    if (data.length === 0) {
      container.innerHTML = '<p class="loader">目前還沒有任何分析紀錄。</p>';
      return;
    }
    
    container.innerHTML = ''; // 移除讀取中
    
    data.forEach(item => {
      const card = document.createElement('div');
      card.className = 'card';
      
      const header = document.createElement('div');
      header.className = 'card-header';
      
      const title = document.createElement('h2');
      title.className = 'card-title';
      title.innerHTML = `<a href="${item.url}" target="_blank" rel="noopener noreferrer">影片 ID: ${item.id}</a>`;
      
      const date = document.createElement('span');
      date.className = 'card-date';
      date.textContent = item.date;
      
      header.appendChild(title);
      header.appendChild(date);
      
      const body = document.createElement('div');
      body.className = 'card-body';
      body.textContent = item.digest;
      
      card.appendChild(header);
      card.appendChild(body);
      
      container.appendChild(card);
    });
    
  } catch (error) {
    console.error('Failed to fetch digest data:', error);
    container.innerHTML = `<p class="loader" style="color: #ef4444;">讀取資料失敗：請確認 history.json 已正確生成並放到 public/data.json</p>`;
  }
});
