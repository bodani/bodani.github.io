// ========== 页面加载完成后执行的初始化代码 ==========

document.addEventListener('DOMContentLoaded', function () {
    // 初始化所有自定义功能
    initializeSmoothScrolling();
    initializeHeaderEnhancements();
    initializeAccessibilityFeatures();
    initializePageLoadEffects();
    initializeBackToTopButton();
    initializeCustomAnimations();
});

// ========== 1. 平滑滚动功能 ==========
function initializeSmoothScrolling() {
    // 为页面内锚点链接添加平滑滚动
    const anchors = document.querySelectorAll('a[href^="#"]');

    anchors.forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            const targetElement = document.querySelector(targetId);

            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 70, // 考虑固定头部高度
                    behavior: 'smooth'
                });
            }
        });
    });
}

// ========== 2. 头部增强 ==========
function initializeHeaderEnhancements() {
    const header = document.querySelector('.md-header');

    if (header) {
        // 页面滚动时的头部视觉增强
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }
        });
    }
}

// ========== 3. 辅助功能增强 ==========
function initializeAccessibilityFeatures() {
    // 为可-clickable元素添加键盘支持
    const clickableElements = document.querySelectorAll('a, button, [role="button"]');

    clickableElements.forEach(element => {
        element.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                if (element.click) {
                    element.click();
                }
            }
        });
    });

    // 改进焦点可见性
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
            document.body.classList.add('keyboard-nav');
        }
    });

    document.addEventListener('mousedown', () => {
        document.body.classList.remove('keyboard-nav');
    });
}

// ========== 4. 页面加载效果 ==========
function initializePageLoadEffects() {
    // 页面载入动画 - 仅标识页面已加载，无额外动画效果
    document.body.classList.add('page-loaded');
}

// ========== 5. 返回顶部按钮 ==========
function initializeBackToTopButton() {
    // 创建返回顶部按钮
    const backToTopButton = document.createElement('div');
    backToTopButton.className = 'back-to-top';
    backToTopButton.innerHTML = '↑';
    backToTopButton.title = '返回顶部';

    // 添加样式
    Object.assign(backToTopButton.style, {
        position: 'fixed',
        bottom: '30px',
        right: '30px',
        backgroundColor: 'var(--md-primary-fg-color)',
        color: 'white',
        width: '40px',
        height: '40px',
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'pointer',
        zIndex: '1000',
        opacity: '0',
        transform: 'translateY(20px)',
        transition: 'all 0.3s ease',
        fontSize: '1.2em',
        fontWeight: 'bold',
        boxShadow: '0 4px 8px rgba(0,0,0,0.2)',
        fontWeight: 'bold'
    });

    document.body.appendChild(backToTopButton);

    // 滚动时控制按钮显示/隐藏
    window.addEventListener('scroll', () => {
        if (window.scrollY > 300) {
            backToTopButton.style.opacity = '1';
            backToTopButton.style.transform = 'translateY(0)';
        } else {
            backToTopButton.style.opacity = '0';
            backToTopButton.style.transform = 'translateY(20px)';
        }
    });

    // 点击按钮滚动到顶部
    backToTopButton.addEventListener('click', () => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

// ========== 6. 自定义动画 ==========
function initializeCustomAnimations() {
    // 监听滚动事件，为元素添加进入视窗动画
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
            }
        });
    }, observerOptions);

    // 选择需要动画的元素
    const animateElements = document.querySelectorAll('.md-content__inner h1, .md-content__inner h2, .md-content__inner p, .grid-cards-container, .card-item');
    animateElements.forEach(el => {
        el.classList.add('will-animate');
        observer.observe(el);
    });
}

// ========== 7. 暗色/亮色主题切换优化 ==========
document.addEventListener('DOMContentLoaded', function () {
    // 主题切换增强
    const paletteOptions = document.querySelectorAll('input[name="__palette"]');

    paletteOptions.forEach(option => {
        option.addEventListener('change', function () {
            // 添加主题切换动画
            document.body.classList.add('theme-changing');
            setTimeout(() => {
                document.body.classList.remove('theme-changing');
            }, 300);
        });
    });
});

// ========== 8. 表格响应式处理 ==========
document.addEventListener('DOMContentLoaded', function () {
    // 为表格添加水平滚动支持
    const tables = document.querySelectorAll('.md-typeset table');

    tables.forEach(table => {
        if (table.offsetWidth > table.parentElement.offsetWidth) {
            const tableWrapper = document.createElement('div');
            tableWrapper.style.overflowX = 'auto';
            tableWrapper.style.margin = '1em 0';
            tableWrapper.style.padding = '0 0.5em';
            table.parentNode.insertBefore(tableWrapper, table);
            tableWrapper.appendChild(table);
        }
    });
});

// ========== 9. 代码块增强 ==========
document.addEventListener('DOMContentLoaded', function () {
    // 为代码块添加行号
    const codeBlocks = document.querySelectorAll('.highlight');

    codeBlocks.forEach(block => {
        if (!block.classList.contains('with-line-numbers')) {
            // 添加行号功能
            const lines = block.textContent.split('\n');
            if (lines.length > 1 && lines[lines.length - 1] === '') {
                lines.pop(); // 移除最后一个空行
            }

            let numberedCode = '<div class="code-block-wrapper">';
            numberedCode += '<table class="code-table"><tbody>';

            lines.forEach((line, i) => {
                numberedCode += `<tr><td class="line-number">${i + 1}</td><td class="line-content">${escapeHtml(line)}</td></tr>`;
            });

            numberedCode += '</tbody></table></div>';
            block.innerHTML = numberedCode;
            block.classList.add('with-line-numbers');
        }
    });
});

// 通用函数：HTML转义 - 解决引号转义问题的版本
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return String(unsafe)
        .replace(/&/g, '&')
        .replace(/</g, '<')
        .replace(/>/g, '>')
        .replace(/"/g, '"')
        .replace(/'/g, '&#039;');
}

// ========== 10. 性能优化：懒加载 (如果需要) ==========
// 如果站点有图片资源，则启用懒加载
function initializeLazyLoading() {
    const images = document.querySelectorAll('img[data-src]');

    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    img.classList.add('loaded');
                    observer.unobserve(img);
                }
            });
        });

        images.forEach(img => imageObserver.observe(img));
    } else {
        // 降级方案：立即加载图片
        const images = document.querySelectorAll('img[data-src]');
        images.forEach(img => {
            img.src = img.dataset.src;
        });
    }
}

// 页面完全加载后初始化懒加载
window.addEventListener('load', initializeLazyLoading);

// ========== 全球样式和效果增强 ==========
// 为页面添加自定义样式类
document.addEventListener('DOMContentLoaded', () => {
    // 添加全局类以便CSS可以识别页面加载状态
    document.documentElement.classList.add('js-enabled');
});
