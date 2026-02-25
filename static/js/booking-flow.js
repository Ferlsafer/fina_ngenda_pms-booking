// Booking Flow State
let bookingState = {
    currentStep: 1,
    guestId: null,
    guest: null,
    roomTypeId: null,
    roomId: null,
    checkIn: null,
    checkOut: null,
    adults: 1,
    children: 0,
    totalAmount: 0,
    bookingReference: null
};

// Initialize booking modal
document.addEventListener('DOMContentLoaded', function() {
    const bookingModal = document.getElementById('bookingModal');
    if (bookingModal) {
        bookingModal.addEventListener('show.bs.modal', function() {
            resetBookingFlow();
        });
    }
    
    // Guest search
    const guestSearch = document.getElementById('guest-search');
    if (guestSearch) {
        guestSearch.addEventListener('input', debounce(searchGuests, 300));
    }
    
    // New guest toggle
    document.getElementById('show-new-guest')?.addEventListener('click', function() {
        document.getElementById('new-guest-form').style.display = 'block';
        this.style.display = 'none';
    });
    
    // Date inputs
    document.getElementById('check-in-date')?.addEventListener('change', checkAvailability);
    document.getElementById('check-out-date')?.addEventListener('change', checkAvailability);
    
    // Next/Prev buttons
    document.getElementById('next-step')?.addEventListener('click', nextStep);
    document.getElementById('prev-step')?.addEventListener('click', prevStep);
    document.getElementById('complete-booking')?.addEventListener('click', completeBooking);
    
    // Payment method toggle
    document.querySelectorAll('input[name="payment_method"]').forEach(radio => {
        radio.addEventListener('change', togglePaymentOptions);
    });
});

// Step navigation
function nextStep() {
    if (bookingState.currentStep === 1) {
        // Validate guest selection
        if (!validateGuestStep()) return;
        bookingState.currentStep = 2;
        updateStepDisplay();
        
    } else if (bookingState.currentStep === 2) {
        // Validate room selection
        if (!validateRoomStep()) return;
        bookingState.currentStep = 3;
        updateStepDisplay();
        updateBookingSummary();
    }
}

function prevStep() {
    if (bookingState.currentStep > 1) {
        bookingState.currentStep--;
        updateStepDisplay();
    }
}

function updateStepDisplay() {
    // Update step indicators
    for (let i = 1; i <= 3; i++) {
        const indicator = document.getElementById(`step${i}-indicator`);
        if (i <= bookingState.currentStep) {
            indicator.classList.add('active');
        } else {
            indicator.classList.remove('active');
        }
    }
    
    // Show/hide step content
    for (let i = 1; i <= 3; i++) {
        const step = document.getElementById(`step${i}`);
        if (i === bookingState.currentStep) {
            step.classList.add('active');
        } else {
            step.classList.remove('active');
        }
    }
    
    // Update buttons
    document.getElementById('prev-step').style.display = bookingState.currentStep > 1 ? 'inline-block' : 'none';
    
    if (bookingState.currentStep === 3) {
        document.getElementById('next-step').style.display = 'none';
        document.getElementById('complete-booking').style.display = 'inline-block';
    } else {
        document.getElementById('next-step').style.display = 'inline-block';
        document.getElementById('complete-booking').style.display = 'none';
    }
}

// Guest validation
function validateGuestStep() {
    if (bookingState.guestId) {
        return true;
    }
    
    // Check if new guest form is filled
    const name = document.getElementById('new-guest-name')?.value;
    const email = document.getElementById('new-guest-email')?.value;
    const phone = document.getElementById('new-guest-phone')?.value;
    
    if (name && email && phone) {
        // Create new guest via API
        createNewGuest({ name, email, phone });
        return true;
    }
    
    alert('Please select a guest or fill in new guest details');
    return false;
}

async function createNewGuest(guestData) {
    try {
        const response = await fetch('/api/payments/guests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(guestData)
        });
        
        const data = await response.json();
        if (data.success) {
            bookingState.guestId = data.guest.id;
            bookingState.guest = data.guest;
        }
    } catch (error) {
        console.error('Error creating guest:', error);
    }
}

// Room availability
async function checkAvailability() {
    const checkIn = document.getElementById('check-in-date').value;
    const checkOut = document.getElementById('check-out-date').value;
    
    if (!checkIn || !checkOut) return;
    
    bookingState.checkIn = checkIn;
    bookingState.checkOut = checkOut;
    
    const roomsList = document.getElementById('rooms-list');
    roomsList.innerHTML = '<div class="text-center py-4"><div class="spinner-border text-primary"></div><p>Checking availability...</p></div>';
    
    try {
        const response = await fetch(`/api/payments/availability?check_in=${checkIn}&check_out=${checkOut}`);
        const data = await response.json();
        
        if (data.success && data.availability) {
            displayAvailableRooms(data.availability);
        }
    } catch (error) {
        roomsList.innerHTML = '<div class="text-center text-danger">Error checking availability</div>';
    }
}

function displayAvailableRooms(rooms) {
    const roomsList = document.getElementById('rooms-list');
    
    if (rooms.length === 0) {
        roomsList.innerHTML = '<div class="alert alert-warning">No rooms available for selected dates</div>';
        return;
    }
    
    let html = '';
    rooms.forEach(room => {
        html += `
            <div class="col-md-6 mb-3">
                <div class="card room-card" data-room-type-id="${room.room_type_id}" data-price="${room.price_per_night}">
                    <div class="card-body">
                        <h5 class="card-title">${room.name}</h5>
                        <p class="text-muted small">${room.available} rooms available</p>
                        <p class="h5">${room.price_per_night} TZS/night</p>
                        <button class="btn btn-outline-primary w-100 select-room" 
                                onclick="selectRoom(${room.room_type_id}, '${room.name}', ${room.price_per_night})">
                            Select
                        </button>
                    </div>
                </div>
            </div>
        `;
    });
    
    roomsList.innerHTML = `<div class="row">${html}</div>`;
}

function selectRoom(roomTypeId, roomName, pricePerNight) {
    bookingState.roomTypeId = roomTypeId;
    bookingState.roomName = roomName;
    bookingState.pricePerNight = pricePerNight;
    
    // Calculate total
    const nights = calculateNights();
    bookingState.totalAmount = pricePerNight * nights;
    
    // Highlight selected room
    document.querySelectorAll('.room-card').forEach(card => {
        card.classList.remove('border-primary', 'selected');
    });
    event.target.closest('.room-card').classList.add('border-primary', 'selected');
}

function validateRoomStep() {
    if (!bookingState.roomTypeId) {
        alert('Please select a room');
        return false;
    }
    if (!bookingState.checkIn || !bookingState.checkOut) {
        alert('Please select check-in and check-out dates');
        return false;
    }
    return true;
}

// Booking summary
function updateBookingSummary() {
    document.getElementById('summary-room').textContent = bookingState.roomName || '-';
    document.getElementById('summary-dates').textContent = 
        `${bookingState.checkIn} to ${bookingState.checkOut}`;
    
    const nights = calculateNights();
    document.getElementById('summary-nights').textContent = nights;
    
    const adults = document.getElementById('adults').value;
    const children = document.getElementById('children').value;
    document.getElementById('summary-guests').textContent = 
        `${adults} Adult${adults > 1 ? 's' : ''}${children > 0 ? `, ${children} Child${children > 1 ? 'ren' : ''}` : ''}`;
    
    document.getElementById('summary-total').textContent = 
        `${bookingState.totalAmount.toLocaleString()} TZS`;
}

function calculateNights() {
    const checkIn = new Date(bookingState.checkIn);
    const checkOut = new Date(bookingState.checkOut);
    const diffTime = Math.abs(checkOut - checkIn);
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
}

// Complete booking
async function completeBooking() {
    const paymentMethod = document.querySelector('input[name="payment_method"]:checked').value;
    
    // Prepare booking data
    const bookingData = {
        guest_id: bookingState.guestId,
        room_type_id: bookingState.roomTypeId,
        check_in: bookingState.checkIn,
        check_out: bookingState.checkOut,
        adults: parseInt(document.getElementById('adults').value),
        children: parseInt(document.getElementById('children').value),
        payment_method: paymentMethod
    };
    
    // Show loading
    document.getElementById('complete-booking').disabled = true;
    document.getElementById('complete-booking').innerHTML = 
        '<span class="spinner-border spinner-border-sm"></span> Processing...';
    
    try {
        // Create booking
        const bookingResponse = await fetch('/api/bookings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(bookingData)
        });
        
        const bookingResult = await bookingResponse.json();
        
        if (!bookingResult.success) {
            throw new Error(bookingResult.error || 'Booking failed');
        }
        
        bookingState.bookingReference = bookingResult.booking_reference;
        
        // Handle payment
        if (paymentMethod === 'mobile_money') {
            await processMobileMoneyPayment(bookingResult.booking_id);
        } else {
            // Pay later - just show success
            showSuccessModal(bookingResult.booking_reference);
        }
        
    } catch (error) {
        alert('Booking failed: ' + error.message);
        document.getElementById('complete-booking').disabled = false;
        document.getElementById('complete-booking').innerHTML = 'Confirm Booking';
    }
}

async function processMobileMoneyPayment(bookingId) {
    const phone = document.getElementById('mobile-phone').value;
    const network = document.getElementById('mobile-network').value;
    
    if (!phone) {
        alert('Please enter phone number');
        return;
    }
    
    // Show Selcom modal
    const selcomModal = new bootstrap.Modal(document.getElementById('selcomPaymentModal'));
    selcomModal.show();
    
    try {
        // Initialize payment
        const paymentResponse = await fetch('/api/payments/initialize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                booking_id: bookingId,
                payment_method: 'mobile_money',
                phone: phone,
                network: network
            })
        });
        
        const paymentResult = await paymentResponse.json();
        
        if (!paymentResult.success) {
            throw new Error(paymentResult.error);
        }
        
        // Update modal to step 2
        document.getElementById('payment-step-1').style.display = 'none';
        document.getElementById('payment-step-2').style.display = 'block';
        document.getElementById('payment-phone').textContent = phone;
        
        // Start polling for payment status
        pollPaymentStatus(paymentResult.transaction_id);
        
    } catch (error) {
        document.getElementById('payment-step-1').style.display = 'none';
        document.getElementById('payment-step-4').style.display = 'block';
        document.getElementById('payment-error-message').textContent = error.message;
    }
}

function pollPaymentStatus(transactionId) {
    let attempts = 0;
    const maxAttempts = 30; // 30 attempts * 2 seconds = 60 seconds
    const timerElement = document.getElementById('payment-timer');
    
    const interval = setInterval(async () => {
        attempts++;
        timerElement.textContent = maxAttempts - attempts;
        
        try {
            const response = await fetch(`/api/payments/status/${transactionId}`);
            const data = await response.json();
            
            if (data.status === 'completed') {
                clearInterval(interval);
                document.getElementById('payment-step-2').style.display = 'none';
                document.getElementById('payment-step-3').style.display = 'block';
                document.getElementById('payment-booking-ref').textContent = data.booking_reference;
                
                // Close modal after 3 seconds and redirect
                setTimeout(() => {
                    bootstrap.Modal.getInstance(document.getElementById('selcomPaymentModal')).hide();
                    window.location.href = `/booking/success/${data.booking_reference}`;
                }, 3000);
                
            } else if (data.status === 'failed') {
                clearInterval(interval);
                document.getElementById('payment-step-2').style.display = 'none';
                document.getElementById('payment-step-4').style.display = 'block';
            }
            
        } catch (error) {
            console.error('Payment status check failed:', error);
        }
        
        if (attempts >= maxAttempts) {
            clearInterval(interval);
            document.getElementById('payment-step-2').style.display = 'none';
            document.getElementById('payment-step-4').style.display = 'block';
            document.getElementById('payment-error-message').textContent = 'Payment timeout. Please try again.';
        }
    }, 2000);
}

function showSuccessModal(bookingRef) {
    // Hide booking modal
    bootstrap.Modal.getInstance(document.getElementById('bookingModal')).hide();
    
    // Show success message
    alert(`Booking confirmed! Reference: ${bookingRef}`);
    window.location.href = `/booking/success/${bookingRef}`;
}

// Helper functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function togglePaymentOptions() {
    const method = this.value;
    
    document.getElementById('mobile-money-options').style.display = 
        method === 'mobile_money' ? 'block' : 'none';
    document.getElementById('card-payment-options').style.display = 
        method === 'card' ? 'block' : 'none';
    document.getElementById('pay-later-options').style.display = 
        method === 'pay_later' ? 'block' : 'none';
}

function resetBookingFlow() {
    bookingState = {
        currentStep: 1,
        guestId: null,
        guest: null,
        roomTypeId: null,
        roomId: null,
        checkIn: null,
        checkOut: null,
        adults: 1,
        children: 0,
        totalAmount: 0,
        bookingReference: null
    };
    
    updateStepDisplay();
    
    // Reset forms
    document.getElementById('guest-search').value = '';
    document.getElementById('new-guest-form').style.display = 'none';
    document.getElementById('show-new-guest').style.display = 'block';
    document.getElementById('check-in-date').value = '';
    document.getElementById('check-out-date').value = '';
    document.getElementById('rooms-list').innerHTML = 
        '<div class="text-center py-4">Select dates to see available rooms</div>';
}
