// thumbanana JavaScript Functions

// 전역 유틸리티 함수들
const utils = {
    // 파일 크기를 읽기 쉬운 형태로 변환
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    // 파일 타입 검증
    validateImageFile(file) {
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
        const maxSize = 10 * 1024 * 1024; // 10MB
        
        if (!allowedTypes.includes(file.type)) {
            return { valid: false, error: '지원하지 않는 파일 형식입니다. JPG, PNG, GIF만 가능합니다.' };
        }
        
        if (file.size > maxSize) {
            return { valid: false, error: '파일 크기는 10MB 이하만 가능합니다.' };
        }
        
        return { valid: true };
    },

    // 디바운스 함수
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // 로컬 스토리지 헬퍼
    storage: {
        set(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
            } catch (e) {
                console.warn('localStorage not available:', e);
            }
        },
        
        get(key) {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : null;
            } catch (e) {
                console.warn('localStorage not available:', e);
                return null;
            }
        },
        
        remove(key) {
            try {
                localStorage.removeItem(key);
            } catch (e) {
                console.warn('localStorage not available:', e);
            }
        }
    },

    // API 헬퍼
    async apiCall(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const config = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API call failed:', error);
            throw error;
        }
    }
};

// 알림 시스템
const notifications = {
    container: null,
    
    init() {
        // 알림 컨테이너 생성
        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.className = 'fixed top-4 right-4 z-50 space-y-2';
        document.body.appendChild(this.container);
    },
    
    show(message, type = 'info', duration = 5000) {
        if (!this.container) this.init();
        
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} transform transition-all duration-300 translate-x-full opacity-0`;
        
        const colors = {
            success: 'bg-green-100 border-green-300 text-green-800',
            error: 'bg-red-100 border-red-300 text-red-800',
            warning: 'bg-yellow-100 border-yellow-300 text-yellow-800',
            info: 'bg-blue-100 border-blue-300 text-blue-800'
        };
        
        notification.className = `${colors[type]} border rounded-lg p-4 shadow-lg max-w-sm transform transition-all duration-300 translate-x-full opacity-0`;
        
        notification.innerHTML = `
            <div class="flex items-center justify-between">
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-gray-500 hover:text-gray-700">
                    <span aria-hidden="true">&times;</span>
                </button>
            </div>
        `;
        
        this.container.appendChild(notification);
        
        // 애니메이션
        setTimeout(() => {
            notification.classList.remove('translate-x-full', 'opacity-0');
        }, 100);
        
        // 자동 제거
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.classList.add('translate-x-full', 'opacity-0');
                    setTimeout(() => {
                        if (notification.parentNode) {
                            notification.remove();
                        }
                    }, 300);
                }
            }, duration);
        }
    }
};

// 이미지 압축 및 리사이징
const imageProcessor = {
    async compressImage(file, maxWidth = 1920, quality = 0.8) {
        return new Promise((resolve) => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();
            
            img.onload = () => {
                // 비율 계산
                let { width, height } = img;
                
                if (width > maxWidth) {
                    height = (height * maxWidth) / width;
                    width = maxWidth;
                }
                
                canvas.width = width;
                canvas.height = height;
                
                // 이미지 그리기
                ctx.drawImage(img, 0, 0, width, height);
                
                // Blob으로 변환
                canvas.toBlob(resolve, file.type, quality);
            };
            
            img.src = URL.createObjectURL(file);
        });
    },
    
    async createThumbnail(file, size = 150) {
        return new Promise((resolve) => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();
            
            img.onload = () => {
                const { width, height } = img;
                
                // 정사각형 썸네일 생성
                const minDimension = Math.min(width, height);
                const scale = size / minDimension;
                
                canvas.width = size;
                canvas.height = size;
                
                const sourceX = (width - minDimension) / 2;
                const sourceY = (height - minDimension) / 2;
                
                ctx.drawImage(
                    img, 
                    sourceX, sourceY, minDimension, minDimension,
                    0, 0, size, size
                );
                
                canvas.toBlob(resolve, 'image/jpeg', 0.8);
            };
            
            img.src = URL.createObjectURL(file);
        });
    }
};

// 폼 검증
const validation = {
    rules: {
        required: (value) => value.trim() !== '',
        email: (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
        minLength: (min) => (value) => value.length >= min,
        maxLength: (max) => (value) => value.length <= max,
        fileSize: (maxSize) => (file) => file.size <= maxSize,
        fileType: (types) => (file) => types.includes(file.type)
    },
    
    messages: {
        required: '필수 입력 항목입니다.',
        email: '올바른 이메일 주소를 입력하세요.',
        minLength: (min) => `최소 ${min}자 이상 입력하세요.`,
        maxLength: (max) => `최대 ${max}자까지 입력 가능합니다.`,
        fileSize: (maxSize) => `파일 크기는 ${utils.formatFileSize(maxSize)} 이하만 가능합니다.`,
        fileType: (types) => `지원하는 파일 형식: ${types.join(', ')}`
    },
    
    validate(value, rules) {
        for (const [ruleName, ruleValue] of Object.entries(rules)) {
            const validator = typeof this.rules[ruleName] === 'function' 
                ? this.rules[ruleName](ruleValue) 
                : this.rules[ruleName];
                
            if (!validator(value)) {
                const messageGenerator = this.messages[ruleName];
                return {
                    valid: false,
                    message: typeof messageGenerator === 'function' 
                        ? messageGenerator(ruleValue) 
                        : messageGenerator
                };
            }
        }
        return { valid: true };
    }
};

// 분석 및 추적
const analytics = {
    track(event, properties = {}) {
        // 개발 환경에서는 콘솔에 로그
        if (window.location.hostname === 'localhost') {
            console.log('Analytics:', event, properties);
            return;
        }
        
        // 프로덕션에서는 실제 분석 도구로 전송
        // TODO: Google Analytics, Mixpanel 등 연동
    },
    
    trackPageView(page = window.location.pathname) {
        this.track('page_view', { page });
    },
    
    trackThumbnailGeneration(data) {
        this.track('thumbnail_generated', {
            style: data.style,
            hasReferenceImages: data.referenceImages.length > 0,
            variants: data.variants,
            titleLength: data.title.length
        });
    },
    
    trackUserAction(action, context = {}) {
        this.track('user_action', { action, ...context });
    }
};

// 키보드 단축키
const shortcuts = {
    init() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + Enter: 폼 제출
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                const activeForm = document.activeElement.closest('form');
                if (activeForm) {
                    e.preventDefault();
                    activeForm.dispatchEvent(new Event('submit'));
                }
            }
            
            // Escape: 모달 닫기
            if (e.key === 'Escape') {
                const modals = document.querySelectorAll('.modal.active, [x-data] .modal[x-show="true"]');
                modals.forEach(modal => {
                    // Alpine.js 모달인 경우
                    const alpineData = modal._x_dataStack?.[0];
                    if (alpineData && alpineData.showModal !== undefined) {
                        alpineData.showModal = false;
                    }
                    // 일반 모달인 경우
                    modal.classList.remove('active');
                });
            }
        });
    }
};

// 다크모드 지원
const darkMode = {
    init() {
        const saved = utils.storage.get('darkMode');
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        if (saved !== null) {
            this.toggle(saved);
        } else if (prefersDark) {
            this.toggle(true);
        }
        
        // 시스템 테마 변경 감지
        window.matchMedia('(prefers-color-scheme: dark)').addListener((e) => {
            if (utils.storage.get('darkMode') === null) {
                this.toggle(e.matches);
            }
        });
    },
    
    toggle(enable = null) {
        const isDark = enable !== null ? enable : !document.documentElement.classList.contains('dark');
        
        if (isDark) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
        
        utils.storage.set('darkMode', isDark);
        analytics.track('dark_mode_toggle', { enabled: isDark });
    }
};

// 초기화
document.addEventListener('DOMContentLoaded', () => {
    // 시스템 초기화
    notifications.init();
    shortcuts.init();
    // darkMode.init(); // 다크모드는 추후 구현
    
    // 페이지 뷰 추적
    analytics.trackPageView();
    
    // 전역적으로 사용할 수 있도록 window 객체에 추가
    window.thumbanana = {
        utils,
        notifications,
        imageProcessor,
        validation,
        analytics,
        shortcuts,
        darkMode
    };
    
    console.log('🍌 thumbanana 클라이언트 초기화 완료!');
});

// 에러 핸들링
window.addEventListener('error', (e) => {
    console.error('JavaScript error:', e.error);
    analytics.track('javascript_error', {
        message: e.error.message,
        filename: e.filename,
        lineno: e.lineno
    });
});

window.addEventListener('unhandledrejection', (e) => {
    console.error('Unhandled promise rejection:', e.reason);
    analytics.track('promise_rejection', {
        reason: e.reason.toString()
    });
});