/**
 * Zotero RAG Demo 聊天功能
 */

// 全局变量
const API_BASE_URL = 'http://localhost:8000/api';
let chatHistory = [];
let settings = {
    maxSources: 5,
    similarityThreshold: 0.6
};

// 初始化Markdown解析器
const md = window.markdownit({
    breaks: true,
    linkify: true,
    typographer: true
});

// DOM元素
const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-btn');
const clearButton = document.getElementById('clear-btn');
const statusButton = document.getElementById('status-btn');
const settingsButton = document.getElementById('settings-btn');
const statusModal = document.getElementById('status-modal');
const settingsModal = document.getElementById('settings-modal');
const modalCloseButtons = document.querySelectorAll('.modal-close');
const saveSettingsButton = document.getElementById('save-settings');
const similarityThreshold = document.getElementById('similarity-threshold');
const thresholdValue = document.getElementById('threshold-value');

// 事件监听器
document.addEventListener('DOMContentLoaded', () => {
    // 发送按钮点击事件
    sendButton.addEventListener('click', sendMessage);
    
    // 输入框Enter键事件
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // 清除按钮事件
    clearButton.addEventListener('click', clearChat);
    
    // 状态按钮事件
    statusButton.addEventListener('click', showStatusModal);
    
    // 设置按钮事件
    settingsButton.addEventListener('click', showSettingsModal);
    
    // 关闭模态框按钮事件
    modalCloseButtons.forEach(button => {
        button.addEventListener('click', () => {
            statusModal.classList.add('hidden');
            settingsModal.classList.add('hidden');
        });
    });
    
    // 保存设置按钮事件
    saveSettingsButton.addEventListener('click', saveSettings);
    
    // 相似度阈值滑块事件
    similarityThreshold.addEventListener('input', () => {
        thresholdValue.textContent = similarityThreshold.value;
    });
    
    // 加载设置
    loadSettings();
});

/**
 * 发送消息
 */
function sendMessage() {
    const query = userInput.value.trim();
    
    if (!query) return;
    
    // 添加用户消息到聊天区域
    addMessageToChat('user', query);
    
    // 清空输入框
    userInput.value = '';
    
    // 显示加载中消息
    const loadingMsgId = addLoadingMessage();
    
    // 保存到历史记录
    chatHistory.push({ role: 'user', content: query });
    
    // 发送API请求
    fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            query: query,
            history: chatHistory,
            max_sources: settings.maxSources,
            similarity_threshold: settings.similarityThreshold
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP错误! 状态: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        // 移除加载中消息
        removeLoadingMessage(loadingMsgId);
        
        // 添加助手回复到聊天区域
        addMessageToChat('assistant', data.answer, data.sources);
        
        // 保存到历史记录
        chatHistory.push({ role: 'assistant', content: data.answer });
        
        // 滚动到底部
        scrollToBottom();
    })
    .catch(error => {
        // 移除加载中消息
        removeLoadingMessage(loadingMsgId);
        
        // 显示错误消息
        addErrorMessage(error.message);
        console.error('API请求错误:', error);
    });
}

/**
 * 添加消息到聊天区域
 * @param {string} role - 消息角色 ('user' 或 'assistant')
 * @param {string} content - 消息内容
 * @param {Array} sources - 引用源 (可选)
 */
function addMessageToChat(role, content, sources = []) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message mb-4`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content rounded-lg p-3';
    
    // 处理Markdown和代码格式
    const formattedContent = md.render(content);
    contentDiv.innerHTML = `<div class="markdown-content">${formattedContent}</div>`;
    
    messageDiv.appendChild(contentDiv);
    
    // 如果是助手消息并且有引用源，添加引用源
    if (role === 'assistant' && sources && sources.length > 0) {
        const sourcesContainer = document.createElement('div');
        sourcesContainer.className = 'sources-container mt-2';
        
        const sourcesToggle = document.createElement('button');
        sourcesToggle.className = 'sources-toggle text-blue-600 text-sm';
        sourcesToggle.textContent = `显示 ${sources.length} 个引用源`;
        
        const sourcesList = document.createElement('div');
        sourcesList.className = 'sources-list mt-2 hidden';
        
        sources.forEach(source => {
            const sourceItem = document.createElement('div');
            sourceItem.className = 'source-item';
            
            const sourceTitle = document.createElement('div');
            sourceTitle.className = 'source-title';
            sourceTitle.textContent = source.title;
            
            const sourceMeta = document.createElement('div');
            sourceMeta.className = 'source-meta';
            
            let metaText = '';
            if (source.authors) metaText += `作者: ${source.authors}`;
            if (source.year) metaText += metaText ? ` | 年份: ${source.year}` : `年份: ${source.year}`;
            if (source.publication) metaText += metaText ? ` | 出版物: ${source.publication}` : `出版物: ${source.publication}`;
            
            sourceMeta.textContent = metaText;
            
            const sourceScore = document.createElement('div');
            sourceScore.className = 'source-score text-xs text-gray-500 mt-1';
            sourceScore.textContent = `相关度: ${(source.score * 100).toFixed(1)}%`;
            
            const sourceText = document.createElement('div');
            sourceText.className = 'source-text mt-1';
            sourceText.textContent = source.text;
            
            sourceItem.appendChild(sourceTitle);
            if (metaText) sourceItem.appendChild(sourceMeta);
            sourceItem.appendChild(sourceScore);
            sourceItem.appendChild(sourceText);
            
            // 如果有DOI或URL，添加链接
            if (source.doi || source.url) {
                const sourceLinks = document.createElement('div');
                sourceLinks.className = 'source-links text-xs mt-1';
                
                if (source.doi) {
                    const doiLink = document.createElement('a');
                    doiLink.href = `https://doi.org/${source.doi}`;
                    doiLink.target = '_blank';
                    doiLink.className = 'text-blue-600 mr-3';
                    doiLink.textContent = 'DOI';
                    sourceLinks.appendChild(doiLink);
                }
                
                if (source.url) {
                    const urlLink = document.createElement('a');
                    urlLink.href = source.url;
                    urlLink.target = '_blank';
                    urlLink.className = 'text-blue-600';
                    urlLink.textContent = 'URL';
                    sourceLinks.appendChild(urlLink);
                }
                
                sourceItem.appendChild(sourceLinks);
            }
            
            sourcesList.appendChild(sourceItem);
        });
        
        // 添加切换引用源显示的事件
        sourcesToggle.addEventListener('click', () => {
            const isHidden = sourcesList.classList.contains('hidden');
            if (isHidden) {
                sourcesList.classList.remove('hidden');
                sourcesToggle.textContent = `隐藏引用源`;
            } else {
                sourcesList.classList.add('hidden');
                sourcesToggle.textContent = `显示 ${sources.length} 个引用源`;
            }
        });
        
        sourcesContainer.appendChild(sourcesToggle);
        sourcesContainer.appendChild(sourcesList);
        contentDiv.appendChild(sourcesContainer);
    }
    
    chatContainer.appendChild(messageDiv);
    
    // 滚动到底部
    scrollToBottom();
}

/**
 * 添加加载中消息
 * @returns {string} 加载消息的ID
 */
function addLoadingMessage() {
    const id = 'loading-' + Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant-message mb-4';
    messageDiv.id = id;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content rounded-lg p-3 bg-gray-50';
    
    contentDiv.innerHTML = `
        <div class="loading-dots">
            思考中<span></span><span></span><span></span>
        </div>
    `;
    
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);
    
    // 滚动到底部
    scrollToBottom();
    
    return id;
}

/**
 * 移除加载中消息
 * @param {string} id - 加载消息的ID
 */
function removeLoadingMessage(id) {
    const loadingMessage = document.getElementById(id);
    if (loadingMessage) {
        loadingMessage.remove();
    }
}

/**
 * 添加错误消息
 * @param {string} errorText - 错误文本
 */
function addErrorMessage(errorText) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant-message mb-4';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content rounded-lg p-3 bg-red-50 text-red-700';
    contentDiv.textContent = `出错了: ${errorText}`;
    
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);
    
    // 滚动到底部
    scrollToBottom();
}

/**
 * 滚动聊天容器到底部
 */
function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * 清除聊天记录
 */
function clearChat() {
    // 保留欢迎消息
    const welcomeMessage = chatContainer.querySelector('.message');
    chatContainer.innerHTML = '';
    if (welcomeMessage) {
        chatContainer.appendChild(welcomeMessage);
    }
    
    // 清空历史记录
    chatHistory = [];
}

/**
 * 显示知识库状态模态框
 */
function showStatusModal() {
    // 重置状态显示
    document.getElementById('document-count').textContent = '--';
    document.getElementById('chunk-count').textContent = '--';
    document.getElementById('embedding-model').textContent = '--';
    document.getElementById('last-updated').textContent = '--';
    
    // 显示模态框
    statusModal.classList.remove('hidden');
    
    // 获取知识库状态
    fetch(`${API_BASE_URL}/status`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('document-count').textContent = data.document_count;
            document.getElementById('chunk-count').textContent = data.chunk_count;
            document.getElementById('embedding-model').textContent = data.embedding_model;
            document.getElementById('last-updated').textContent = data.last_updated;
        })
        .catch(error => {
            console.error('获取知识库状态失败:', error);
            document.getElementById('kb-status-content').innerHTML = `
                <div class="error-message">
                    获取知识库状态失败: ${error.message}
                </div>
            `;
        });
}

/**
 * 显示设置模态框
 */
function showSettingsModal() {
    // 更新设置界面
    document.getElementById('max-sources').value = settings.maxSources;
    document.getElementById('similarity-threshold').value = settings.similarityThreshold;
    document.getElementById('threshold-value').textContent = settings.similarityThreshold;
    
    // 显示模态框
    settingsModal.classList.remove('hidden');
}

/**
 * 保存设置
 */
function saveSettings() {
    const maxSources = parseInt(document.getElementById('max-sources').value);
    const similarityThreshold = parseFloat(document.getElementById('similarity-threshold').value);
    
    settings = {
        maxSources: maxSources,
        similarityThreshold: similarityThreshold
    };
    
    // 保存到本地存储
    localStorage.setItem('ragDemoSettings', JSON.stringify(settings));
    
    // 关闭模态框
    settingsModal.classList.add('hidden');
}

/**
 * 加载设置
 */
function loadSettings() {
    const savedSettings = localStorage.getItem('ragDemoSettings');
    if (savedSettings) {
        settings = JSON.parse(savedSettings);
    }
} 