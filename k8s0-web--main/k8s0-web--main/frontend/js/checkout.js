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
            const name = item.product_name || item.name || 'Sản phẩm';
            const price = item.unit_price !== undefined ? item.unit_price : (item.price || 0);
            const img = item.image || item.img || 'images/cat-cues.jpg';
            total += price * item.quantity;
            return `
                <div class="flex gap-4 items-center">
                    <div class="relative">
                        <img src="${img}" class="w-16 h-16 object-cover rounded-lg bg-black" onerror="this.src='images/cat-cues.jpg'">
                        <span class="absolute -top-2 -right-2 bg-gray-600 text-xs w-5 h-5 flex items-center justify-center rounded-full">${item.quantity}</span>
                    </div>
                    <div class="flex-grow">
                        <div class="font-medium text-sm line-clamp-1">${name}</div>
                        <div class="text-xs text-gray-400 mt-1">${App.formatPrice(price)}</div>
                    </div>
                    <div class="font-semibold text-sm">
                        ${App.formatPrice(price * item.quantity)}
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
        const address = document.getElementById('address').value;
        const name = document.getElementById('fullname').value;
        const phone = document.getElementById('phone').value;
        const note = document.getElementById('note').value;
        
        const paymentMethod = document.querySelector('input[name="payment"]:checked').value;

        // 1. Create Order
        const order = await Api.order.create({
            shipping_address: address,
            shipping_name: name,
            shipping_phone: phone,
            note: note,
            payment_method: paymentMethod
        });

        // 2. Process Payment
        await Api.order.checkout({
            order_id: order.id,
            method: paymentMethod
        });

        window.dispatchEvent(new Event('cartUpdated'));
        
        const code = 'BIDA-' + order.id;
        document.getElementById('orderCode').textContent = code;
        document.getElementById('successModal').classList.replace('hidden', 'flex');
        
    } catch (e) {
        showToast(e.message || 'Có lỗi xảy ra khi đặt hàng', 'error');
        btn.innerHTML = 'Xác Nhận Đặt Hàng <i class="fa-solid fa-check"></i>';
        btn.disabled = false;
    }
}
