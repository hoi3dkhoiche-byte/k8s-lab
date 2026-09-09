// Global App Logic

const App = {
    init() {
        this.updateAuthUI();
        this.updateCartBadge();
        
        // Listen to custom cart updates
        window.addEventListener('cartUpdated', () => this.updateCartBadge());
    },
    
    formatPrice(amount) {
        return new Intl.NumberFormat('vi-VN', {
            style: 'currency',
            currency: 'VND'
        }).format(amount);
    },
    
    updateAuthUI() {
        const userMenu = document.getElementById('userMenu');
        const token = Api.getToken();
        
        if (!userMenu) return;

        if (token) {
            const userStr = sessionStorage.getItem('user');
            const user = userStr ? JSON.parse(userStr) : { name: 'Tài khoản' };
            
            userMenu.innerHTML = `
                <button class="text-white hover:text-gold transition flex items-center gap-2">
                    <i class="fa-regular fa-user"></i>
                    <span class="text-sm hidden md:inline">${user.name}</span>
                </button>
                <div class="absolute right-0 mt-2 w-48 glass rounded-xl shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50 overflow-hidden">
                    <a href="orders.html" class="block px-4 py-3 text-sm text-white hover:bg-gold/20 hover:text-gold border-b border-gold/10">Đơn hàng của tôi</a>
                    <a href="#" onclick="App.logout()" class="block px-4 py-3 text-sm text-white hover:bg-red-500/20 hover:text-red-400">Đăng xuất</a>
                </div>
            `;
        }
    },
    
    logout() {
        Api.auth.logout();
        window.location.href = 'index.html';
    },
    
    async updateCartBadge() {
        const badge = document.getElementById('cartBadge');
        if (!badge) return;
        
        try {
            const cart = await Api.cart.getCart();
            const count = cart.items.reduce((acc, item) => acc + item.quantity, 0);
            
            if (count > 0) {
                badge.textContent = count;
                badge.classList.remove('hidden');
            } else {
                badge.classList.add('hidden');
            }
        } catch (error) {
            console.error('Lỗi cập nhật giỏ hàng:', error);
        }
    }
};

// Toast Notifications
function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icon = type === 'success' ? 'fa-check-circle text-green-400' 
               : type === 'error' ? 'fa-exclamation-circle text-red-400' 
               : 'fa-info-circle text-gold';
               
    toast.innerHTML = `
        <i class="fa-solid ${icon} text-xl"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Remove after 3s
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Product Card Renderer
function renderProducts(products, container) {
    if (!products || products.length === 0) {
        container.innerHTML = '<div class="col-span-full text-center text-gray-400 py-16 glass rounded-2xl"><i class="fa-solid fa-box-open text-4xl text-gray-500 mb-3 block"></i>Không tìm thấy sản phẩm nào phù hợp.</div>';
        return;
    }
    
    container.innerHTML = products.map(p => {
        const safeName = (p.name || '').replace(/'/g, "\\'");
        const safeImg = (p.img || '').replace(/'/g, "\\'");
        const categoryLabel = p.category === 'cues' ? 'Gậy Pool' : p.category === 'cases' ? 'Bao & Hộp' : 'Phụ Kiện';

        return `
        <div class="glass product-card flex flex-col h-full bg-navy/40 rounded-2xl overflow-hidden hover:border-gold/60 transition-all duration-300 group">
            <a href="product.html?id=${p.id}" class="product-img-wrapper block h-48 sm:h-56 relative bg-black/50 overflow-hidden cursor-pointer">
                <img src="${p.img || 'images/cat-cues.jpg'}" alt="${p.name}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500">
                <span class="absolute top-3 left-3 bg-dark/90 text-gold text-xs px-2.5 py-1 rounded-full border border-gold/40 uppercase tracking-wider font-semibold">${categoryLabel}</span>
            </a>
            <div class="p-5 flex flex-col flex-grow">
                <a href="product.html?id=${p.id}" class="text-white font-medium text-base hover:text-gold transition line-clamp-2 mb-2 flex-grow block cursor-pointer">
                    ${p.name}
                </a>
                <div class="text-gold font-bold text-lg mb-4">
                    ${App.formatPrice(p.price)}
                </div>
                <div class="grid grid-cols-2 gap-2 mt-auto pt-3 border-t border-gold/15">
                    <button onclick="addToCart(${p.id}, '${safeName}', ${p.price}, '${safeImg}')" class="w-full py-2 px-3 rounded-lg bg-white/5 hover:bg-gold/20 text-gold border border-gold/30 text-xs font-semibold transition flex items-center justify-center gap-1.5" title="Thêm vào giỏ hàng">
                        <i class="fa-solid fa-cart-plus"></i> Thêm giỏ
                    </button>
                    <button onclick="buyNow(${p.id}, '${safeName}', ${p.price}, '${safeImg}')" class="w-full py-2 px-3 rounded-lg btn-primary text-xs font-bold uppercase transition flex items-center justify-center gap-1.5 shadow-md hover:brightness-110" title="Mua ngay và thanh toán">
                        <i class="fa-solid fa-bolt"></i> Mua ngay
                    </button>
                </div>
            </div>
        </div>
        `;
    }).join('');
}

async function addToCart(id, name, price, img) {
    try {
        await Api.cart.addToCart(id, 1, { name, price, img });
        window.dispatchEvent(new Event('cartUpdated'));
        showToast(`Đã thêm "${name}" vào giỏ hàng`);
    } catch (e) {
        showToast('Lỗi thêm vào giỏ hàng', 'error');
    }
}

async function buyNow(id, name, price, img) {
    try {
        await Api.cart.addToCart(id, 1, { name, price, img });
        window.dispatchEvent(new Event('cartUpdated'));
        showToast(`Đang chuyển đến giỏ hàng...`);
        setTimeout(() => {
            window.location.href = 'cart.html';
        }, 300);
    } catch (e) {
        showToast('Lỗi xử lý mua hàng', 'error');
    }
}

function handleSearch() {
    const input = document.getElementById('searchInput');
    if (input && input.value.trim()) {
        window.location.href = `index.html?search=${encodeURIComponent(input.value.trim())}#products`;
    }
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    App.init();
});
