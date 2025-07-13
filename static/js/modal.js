/**
 * 显示模态窗口
 * @param {Object} options 配置选项
 * @param {string} options.url 要加载的URL（可选）
 * @param {string} options.title 模态窗口标题（可选）
 * @param {string} options.content 直接显示的内容（可选）
 * @param {Object} options.size 窗口尺寸 {width, height}（可选）
 * @param {boolean} options.closeOnClickOutside 点击外部是否关闭（默认true）
 */
function showModal(options = {}) {
    // 创建模态窗口容器
    const modal = document.createElement('div');
    modal.id = 'custom-modal';
    modal.style.position = 'fixed';
    modal.style.top = '0';
    modal.style.left = '0';
    modal.style.width = '100%';
    modal.style.height = '100%';
    modal.style.backgroundColor = 'rgba(0,0,0,0.5)';
    modal.style.zIndex = '1000';
    modal.style.display = 'flex';
    modal.style.justifyContent = 'center';
    modal.style.alignItems = 'center';
    
    // 创建内容容器
    const content = document.createElement('div');
    content.style.background = 'white';
    content.style.padding = '20px';
    content.style.borderRadius = '8px';
    content.style.maxHeight = '80vh';
    content.style.overflow = 'auto';
    
    // 设置尺寸
    if (options.size) {
        content.style.width = options.size.width || '600px';
        content.style.height = options.size.height || '400px';
    } else {
        content.style.width = '600px';
        content.style.maxWidth = '90vw';
    }
    
    // 添加关闭按钮
    const closeBtn = document.createElement('button');
    closeBtn.textContent = '×';
    closeBtn.style.position = 'absolute';
    closeBtn.style.right = '10px';
    closeBtn.style.top = '10px';
    closeBtn.style.background = 'none';
    closeBtn.style.border = 'none';
    closeBtn.style.fontSize = '20px';
    closeBtn.style.cursor = 'pointer';
    
    // 添加标题
    if (options.title) {
        const title = document.createElement('h2');
        title.textContent = options.title;
        title.style.marginTop = '0';
        content.appendChild(title);
    }
    
    // 添加内容
    if (options.content) {
        const contentDiv = document.createElement('div');
        contentDiv.innerHTML = options.content;
        content.appendChild(contentDiv);
    }
    
    // 处理URL加载
    if (options.url) {
        const loading = document.createElement('div');
        loading.textContent = '加载中...';
        content.appendChild(loading);
        
        fetch(options.url)
            .then(response => response.text())
            .then(html => {
                loading.remove();
                const iframe = document.createElement('div');
                iframe.innerHTML = html;
                content.appendChild(iframe);
            });
    }
    
    // 组装元素
    content.appendChild(closeBtn);
    modal.appendChild(content);
    document.body.appendChild(modal);
    
    // 关闭逻辑
    closeBtn.onclick = () => modal.remove();
    if (options.closeOnClickOutside !== false) {
        modal.onclick = (e) => {
            if (e.target === modal) modal.remove();
        };
    }
    
    // 返回modal对象以便外部控制
    return {
        element: modal,
        close: () => modal.remove()
    };
}