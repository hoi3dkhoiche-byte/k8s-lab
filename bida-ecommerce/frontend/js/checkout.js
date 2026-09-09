document.addEventListener('DOMContentLoaded', () => {
    loadCheckoutCart();
    
    // Payment radio logic
    const radios = document.querySelectorAll('input[name="payment"]');
    radios.forEach(r => {
        r.addEventListener('change', (e) => {
            radios.forEach(rad => rad.closest('label').classList.replace('bg-gold/10', 'bg-transparent'));
            radios.forEach(rad => rad.closest('label').classList.replace('border-gold/30', 'border-gray-700'));
            
            const label = e.target.closest('label');
            label.classList.add('bg-gold/10', 'border-gold/30');
            label.classList.remove('border-gray-700');
        });
    });

    document.getElementById('submitOrderBtn').addEventListener('click', submitOrder);
});

let cartItems = [];

async function loadCheckoutCart() {
    const container = document.getElementById('checkoutItems');
    try {
        const cart = await Api.cart.getCart();
        cartItems = cart.items;
        
        if (!cartItems || cartItems.length === 0) {
            window.location.href = 'cart.html';
            return;
        }

        let total = 0;
        container.innerHTML = cartItems.map(item => {
            total += item.price * item.quantity;
            return `
                <div class="flex gap-4 items-center">
                    <div class="relative">
                        <img src="${item.img || 'images/cat-cues.jpg'}" class="w-16 h-16 object-cover rounded-lg bg-black">
                        <span class="absolute -top-2 -right-2 bg-gray-600 text-xs w-5 h-5 flex items-center justify-center rounded-full">${item.quantity}</span>
                    </div>
                    <div class="flex-grow">
                        <div class="font-medium text-sm line-clamp-1">${item.name}</div>
                        <div class="text-xs text-gray-400 mt-1">${App.formatPrice(item.price)}</div>
                    </div>
                    <div class="font-semibold text-sm">
                        ${App.formatPrice(item.price * item.quantity)}
                    </div>
                </div>
            `;
        }).join('');

        document.getElementById('subtotalDisplay').textContent = App.formatPrice(total);
        document.getElementById('totalDisplay').textContent = App.formatPrice(total);

    } catch (e) {
        showToast('Lỗi tải thông tin đơn hàng', 'error');
    }
}

async function submitOrder() {
    const form = document.getElementById('checkoutForm');
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const btn = document.getElementById('submitOrderBtn');
    btn.innerHTML = '<div class="spinner w-6 h-6 border-2"></div> Đang xử lý...';
    btn.disabled = true;

    try {
        // Mock API call
        await new Promise(r => setTimeout(r, 1500));
        
        await Api.cart.clear();
        window.dispatchEvent(new Event('cartUpdated'));
        
        const code = 'BIDA-' + Math.floor(Math.random() * 1000000);
        document.getElementById('orderCode').textContent = code;
        document.getElementById('successModal').classList.replace('hidden', 'flex');
        
    } catch (e) {
        showToast('Có lỗi xảy ra khi đặt hàng', 'error');
        btn.innerHTML = 'Xác Nhận Đặt Hàng <i class="fa-solid fa-check"></i>';
        btn.disabled = false;
    }
}
