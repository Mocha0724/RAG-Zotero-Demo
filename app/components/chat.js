/**
 * Zotero RAG Demo 聊天功能
 */

// 全局变量
const API_BASE_URL = 'http://localhost:8000/api';
let chatHistory = []; // 当前对话历史
let settings = {
    maxSources: 5,
    similarityThreshold: 0.6,
    mode: 'rag' // 默认使用知识库模式
};

// 对话管理
let conversations = []; // 所有对话列表
let currentConversationId = null; // 当前对话ID

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
const modeToggle = document.getElementById('mode-toggle');
const modeLabel = document.getElementById('mode-label');

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
    
    // 模式切换事件
    modeToggle.addEventListener('change', () => {
        settings.mode = modeToggle.checked ? 'rag' : 'chat';
        modeLabel.textContent = modeToggle.checked ? '使用知识库' : '纯对话模式';
        
        // 保存设置
        localStorage.setItem('chatSettings', JSON.stringify(settings));
        
        // 添加系统消息提示模式切换
        const modeMessage = modeToggle.checked 
            ? '已切换到知识库查询模式，我将使用您的文献库回答问题。' 
            : '已切换到纯对话模式，我将作为一般AI助手与您交流，不查询知识库。';
        
        addSystemMessage(modeMessage);
    });
    
    // 新建对话按钮
    document.getElementById('new-chat-btn').addEventListener('click', createNewConversation);
    
    // 重命名对话相关事件
    document.getElementById('save-conversation-name').addEventListener('click', saveConversationName);
    
    // 加载设置
    loadSettings();
    
    // 加载对话列表
    loadConversations();
    
    // 重命名模态框关闭
    document.querySelectorAll('.modal-close').forEach(element => {
        element.addEventListener('click', () => {
            const modals = [statusModal, settingsModal, document.getElementById('rename-modal')];
            modals.forEach(modal => {
                if (modal) modal.classList.add('hidden');
            });
        });
    });
    
    // ESC键关闭模态框
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const modals = [statusModal, settingsModal, document.getElementById('rename-modal')];
            modals.forEach(modal => {
                if (modal && !modal.classList.contains('hidden')) {
                    modal.classList.add('hidden');
                }
            });
        }
    });
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
            similarity_threshold: settings.similarityThreshold,
            mode: settings.mode
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
        
        // 更新当前对话
        updateCurrentConversation();
        
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
        
        // 将引用源保存到消息中，以便在加载对话时恢复
        const assistantMsg = chatHistory.find(msg => msg.role === 'assistant' && msg.content === content);
        if (assistantMsg) {
            assistantMsg.sources = sources;
        }
    }
    
    chatContainer.appendChild(messageDiv);
    
    // 滚动到底部
    scrollToBottom();
}

/**
 * 添加加载中消息
 * @returns {string} 加载消息的唯一ID
 */
function addLoadingMessage() {
    const messageId = 'loading-' + Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant-message mb-4';
    messageDiv.id = messageId;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content rounded-lg p-3 bg-blue-50 flex items-center';
    
    contentDiv.innerHTML = `
        <div class="loading-dots flex space-x-1">
            <div class="w-2 h-2 bg-blue-600 rounded-full animate-bounce"></div>
            <div class="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
            <div class="w-2 h-2 bg-blue-600 rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
        </div>
        <div class="ml-3 text-gray-500">思考中...</div>
    `;
    
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);
    
    // 滚动到底部
    scrollToBottom();
    
    return messageId;
}

/**
 * 移除加载中消息
 * @param {string} messageId - 加载消息的唯一ID
 */
function removeLoadingMessage(messageId) {
    const messageElement = document.getElementById(messageId);
    if (messageElement) {
        messageElement.remove();
    }
}

/**
 * 添加错误消息
 * @param {string} errorText - 错误信息
 */
function addErrorMessage(errorText) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message error-message mb-4';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content rounded-lg p-3 bg-red-100 text-red-700';
    contentDiv.textContent = `错误: ${errorText}`;
    
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);
    
    // 滚动到底部
    scrollToBottom();
}

/**
 * 滚动到对话区域底部
 */
function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

/**
 * 清除当前对话内容
 */
function clearChat() {
    if (!confirm('确定要清除当前对话的所有消息吗？此操作不可恢复。')) {
        return;
    }
    
    // 清空聊天历史
    chatHistory = [];
    
    // 清空聊天区域并添加欢迎消息
    document.getElementById('chat-container').innerHTML = '';
    addWelcomeMessage();
    
    // 更新当前对话
    updateCurrentConversation();
    
    // 滚动到底部
    scrollToBottom();
}

/**
 * 显示知识库状态模态框
 */
function showStatusModal() {
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
            document.getElementById('kb-status-content').innerHTML = `<p class="text-red-500">获取知识库状态失败: ${error.message}</p>`;
        });
}

/**
 * 显示设置模态框
 */
function showSettingsModal() {
    // 更新设置UI值
    document.getElementById('max-sources').value = settings.maxSources;
    document.getElementById('similarity-threshold').value = settings.similarityThreshold;
    document.getElementById('threshold-value').textContent = settings.similarityThreshold;
    
    // 显示模态框
    settingsModal.classList.remove('hidden');
}

/**
 * 添加系统消息到聊天区域
 * @param {string} content - 消息内容
 */
function addSystemMessage(content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message system-message mb-4';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content rounded-lg p-3 bg-gray-200 text-center';
    contentDiv.textContent = content;
    
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);
    
    // 滚动到底部
    scrollToBottom();
}

/**
 * 保存设置
 */
function saveSettings() {
    // 获取设置值
    settings.maxSources = parseInt(document.getElementById('max-sources').value);
    settings.similarityThreshold = parseFloat(document.getElementById('similarity-threshold').value);
    
    // 保存设置
    localStorage.setItem('chatSettings', JSON.stringify(settings));
    
    // 更新当前对话中的设置
    updateCurrentConversation();
    
    // 关闭模态框
    settingsModal.classList.add('hidden');
}

/**
 * 加载设置
 */
function loadSettings() {
    // 从本地存储加载设置
    const savedSettings = localStorage.getItem('chatSettings');
    if (savedSettings) {
        const parsed = JSON.parse(savedSettings);
        settings = {...settings, ...parsed};
        
        // 更新UI
        document.getElementById('max-sources').value = settings.maxSources;
        document.getElementById('similarity-threshold').value = settings.similarityThreshold;
        document.getElementById('threshold-value').textContent = settings.similarityThreshold;
        
        // 设置模式开关
        modeToggle.checked = settings.mode === 'rag';
        modeLabel.textContent = modeToggle.checked ? '使用知识库' : '纯对话模式';
    }
}

/**
 * 加载对话列表
 */
function loadConversations() {
    // 从localStorage加载对话列表
    const savedConversations = localStorage.getItem('zoteroRagConversations');
    if (savedConversations) {
        conversations = JSON.parse(savedConversations);
    }
    
    // 如果没有对话，创建一个新对话
    if (conversations.length === 0) {
        createNewConversation();
    } else {
        // 加载最近一次的对话
        const lastConversationId = localStorage.getItem('zoteroRagCurrentConversation') || conversations[0].id;
        loadConversation(lastConversationId);
    }
    
    // 渲染对话列表
    renderConversationsList();
}

/**
 * 渲染对话列表
 */
function renderConversationsList() {
    const listElement = document.getElementById('conversations-list');
    listElement.innerHTML = '';
    
    conversations.forEach(conversation => {
        const item = document.createElement('div');
        item.className = `conversation-item ${conversation.id === currentConversationId ? 'active' : ''}`;
        item.dataset.id = conversation.id;
        
        const itemContent = `
            <div class="conversation-title">${conversation.title}</div>
            <div class="conversation-actions">
                <button class="conversation-action-btn rename-btn" title="重命名">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="conversation-action-btn delete-btn" title="删除">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </div>
        `;
        
        item.innerHTML = itemContent;
        
        // 点击加载对话
        item.addEventListener('click', (event) => {
            // 忽略按钮点击
            if (event.target.closest('.conversation-action-btn')) {
                return;
            }
            loadConversation(conversation.id);
        });
        
        // 重命名按钮事件
        const renameBtn = item.querySelector('.rename-btn');
        renameBtn.addEventListener('click', (event) => {
            event.stopPropagation();
            openRenameModal(conversation.id);
        });
        
        // 删除按钮事件
        const deleteBtn = item.querySelector('.delete-btn');
        deleteBtn.addEventListener('click', (event) => {
            event.stopPropagation();
            deleteConversation(conversation.id);
        });
        
        listElement.appendChild(item);
    });
    
    // 更新当前对话名称显示
    updateCurrentConversationDisplay();
}

/**
 * 创建新对话
 */
function createNewConversation() {
    const newId = 'conv_' + Date.now();
    const newConversation = {
        id: newId,
        title: '新对话',
        createdAt: new Date().toISOString(),
        messages: [],
        settings: { ...settings }
    };
    
    conversations.unshift(newConversation);
    saveConversations();
    
    loadConversation(newId);
}

/**
 * 加载对话
 * @param {string} conversationId - 对话ID
 */
function loadConversation(conversationId) {
    const conversation = conversations.find(c => c.id === conversationId);
    if (!conversation) return;
    
    currentConversationId = conversationId;
    chatHistory = [...conversation.messages]; // 复制消息
    settings = { ...conversation.settings }; // 复制设置
    
    // 更新UI
    document.getElementById('mode-toggle').checked = settings.mode === 'rag';
    document.getElementById('mode-label').textContent = settings.mode === 'rag' ? '使用知识库' : '纯对话模式';
    
    // 清空并重新渲染聊天区域
    const chatContainer = document.getElementById('chat-container');
    chatContainer.innerHTML = '';
    
    // 添加欢迎消息
    if (chatHistory.length === 0) {
        addWelcomeMessage();
    } else {
        // 渲染历史消息
        chatHistory.forEach(msg => {
            if (msg.role === 'user') {
                addMessageToChat('user', msg.content);
            } else if (msg.role === 'assistant') {
                // 尝试获取引用源
                const sources = msg.sources || [];
                addMessageToChat('assistant', msg.content, sources);
            }
        });
    }
    
    // 保存当前对话ID
    localStorage.setItem('zoteroRagCurrentConversation', conversationId);
    
    // 更新对话列表UI
    renderConversationsList();
    
    // 滚动到底部
    scrollToBottom();
}

/**
 * 更新当前对话内容
 */
function updateCurrentConversation() {
    if (!currentConversationId) return;
    
    const index = conversations.findIndex(c => c.id === currentConversationId);
    if (index === -1) return;
    
    conversations[index].messages = [...chatHistory];
    conversations[index].settings = { ...settings };
    conversations[index].updatedAt = new Date().toISOString();
    
    // 如果是第一次添加消息，更新标题
    if (conversations[index].title === '新对话' && chatHistory.length >= 2) {
        const firstUserMessage = chatHistory.find(msg => msg.role === 'user');
        if (firstUserMessage) {
            const title = firstUserMessage.content.substring(0, 30) + (firstUserMessage.content.length > 30 ? '...' : '');
            conversations[index].title = title;
        }
    }
    
    saveConversations();
    renderConversationsList();
}

/**
 * 保存对话列表到localStorage
 */
function saveConversations() {
    localStorage.setItem('zoteroRagConversations', JSON.stringify(conversations));
}

/**
 * 删除对话
 * @param {string} conversationId - 对话ID
 */
function deleteConversation(conversationId) {
    // 确认删除
    if (!confirm('确定要删除这个对话吗？此操作不可恢复。')) {
        return;
    }
    
    const index = conversations.findIndex(c => c.id === conversationId);
    if (index === -1) return;
    
    conversations.splice(index, 1);
    saveConversations();
    
    // 如果删除的是当前对话，加载另一个对话
    if (conversationId === currentConversationId) {
        if (conversations.length > 0) {
            loadConversation(conversations[0].id);
        } else {
            createNewConversation();
        }
    } else {
        renderConversationsList();
    }
}

/**
 * 打开重命名模态框
 * @param {string} conversationId - 对话ID
 */
function openRenameModal(conversationId) {
    const conversation = conversations.find(c => c.id === conversationId);
    if (!conversation) return;
    
    document.getElementById('conversation-name').value = conversation.title;
    document.getElementById('rename-modal').classList.remove('hidden');
    document.getElementById('conversation-name').dataset.id = conversationId;
    document.getElementById('conversation-name').focus();
}

/**
 * 保存对话名称
 */
function saveConversationName() {
    const input = document.getElementById('conversation-name');
    const newName = input.value.trim();
    const conversationId = input.dataset.id;
    
    if (!newName || !conversationId) return;
    
    const index = conversations.findIndex(c => c.id === conversationId);
    if (index === -1) return;
    
    conversations[index].title = newName;
    saveConversations();
    
    // 关闭模态框
    document.getElementById('rename-modal').classList.add('hidden');
    
    // 更新UI
    renderConversationsList();
}

/**
 * 更新当前对话名称显示
 */
function updateCurrentConversationDisplay() {
    const currentConversation = conversations.find(c => c.id === currentConversationId);
    if (currentConversation) {
        document.getElementById('current-conversation-name').textContent = currentConversation.title;
    }
}

/**
 * 添加欢迎消息
 */
function addWelcomeMessage() {
    const welcomeDiv = document.createElement('div');
    welcomeDiv.className = 'message assistant-message mb-4';
    welcomeDiv.innerHTML = `
        <div class="message-content rounded-lg p-3 bg-blue-50">
            <p>👋 欢迎使用Zotero文献助手！</p>
            <p class="mt-2">我可以帮您查找和回答与您知识库相关的问题，也可以作为普通助手与您交流。</p>
            <p class="mt-2">您可以使用右下角的开关在<strong>知识库查询模式</strong>和<strong>纯对话模式</strong>之间切换：</p>
            <ul class="list-disc ml-6 mt-1">
                <li><strong>知识库查询模式</strong>：我将从您的Zotero文献库中检索相关内容回答问题</li>
                <li><strong>纯对话模式</strong>：我将作为普通AI助手与您交流，不查询知识库</li>
            </ul>
        </div>
    `;
    
    document.getElementById('chat-container').appendChild(welcomeDiv);
} 