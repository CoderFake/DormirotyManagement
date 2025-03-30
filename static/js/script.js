/**
 * Hệ thống Quản lý Ký túc xá
 * Tập tin JavaScript chính
 */

document.addEventListener('DOMContentLoaded', function() {

    initTooltipsAndPopovers();

    handleSidebarToggle();

    initCommonEvents();

    initNotifications();

    initSpecialComponents();

    if (document.getElementById('myChart') || 
        document.getElementById('buildingChart') ||
        document.getElementById('revenueChart') ||
        document.getElementById('roomStatusChart')) {
        initCharts();
    }
});

/**
 * Khởi tạo tooltips và popovers
 */
function initTooltipsAndPopovers() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

/**
 * Quản lý toggle sidebar và xử lý responsive
 */
function handleSidebarToggle() {
    const sidebarToggle = document.getElementById('sidebarToggle');
    if (!sidebarToggle) return;
    
    const sidebar = document.querySelector('.sidebar');
    const main = document.querySelector('main');

    function toggleSidebar() {
        sidebar.classList.toggle('toggled');
        main.classList.toggle('sidebar-toggled');

        const sidebarState = sidebar.classList.contains('toggled') ? 'closed' : 'open';
        localStorage.setItem('sidebarState', sidebarState);

        if (sidebar.classList.contains('toggled')) {
            const collapses = sidebar.querySelectorAll('.collapse.show');
            collapses.forEach(item => {
                const bsCollapse = new bootstrap.Collapse(item, {toggle: false});
                bsCollapse.hide();
            });
        }
    }

    sidebarToggle.addEventListener('click', function(e) {
        e.preventDefault();
        toggleSidebar();
    });

    const savedState = localStorage.getItem('sidebarState');
    if (savedState === 'closed') {
        sidebar.classList.add('toggled');
        main.classList.add('sidebar-toggled');
    }

    function handleResize() {
        if (window.innerWidth < 992) {

            sidebar.classList.add('toggled');
            main.classList.remove('sidebar-toggled');

            const collapses = sidebar.querySelectorAll('.collapse.show');
            collapses.forEach(item => {
                const bsCollapse = new bootstrap.Collapse(item, {toggle: false});
                bsCollapse.hide();
            });
        } else if (savedState !== 'closed') {
            sidebar.classList.remove('toggled');
            main.classList.remove('sidebar-toggled');
        }
    }

    window.addEventListener('resize', handleResize);

    handleResize();

    document.addEventListener('click', function(event) {
        if (window.innerWidth < 992 && 
            !sidebar.contains(event.target) && 
            !sidebarToggle.contains(event.target) && 
            !sidebar.classList.contains('toggled')) {
            sidebar.classList.add('toggled');
        }
    });
}

/**
 * Khởi tạo các sự kiện chung
 */
function initCommonEvents() {

    $(window).scroll(function() {
        if ($(this).scrollTop() > 100) {
            $('.scroll-to-top').fadeIn();
        } else {
            $('.scroll-to-top').fadeOut();
        }
    });

    $('.scroll-to-top').click(function() {
        $('html, body').animate({scrollTop: 0}, 800);
        return false;
    });

    $('.btn-delete').on('click', function(e) {
        e.preventDefault();
        var form = $(this).closest('form');
        
        Swal.fire({
            title: 'Bạn có chắc chắn?',
            text: "Dữ liệu sẽ bị xóa và không thể khôi phục!",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#e74a3b',
            cancelButtonColor: '#858796',
            confirmButtonText: 'Xác nhận xóa',
            cancelButtonText: 'Hủy bỏ'
        }).then((result) => {
            if (result.isConfirmed) {
                form.submit();
            }
        });
    });

    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    $('.custom-file-input').on('change', function() {
        let fileName = $(this).val().split('\\').pop();
        $(this).next('.custom-file-label').addClass("selected").html(fileName);
    });

    $('.show-password-toggle').on('click', function() {
        const passwordInput = $(this).closest('.input-group').find('input');
        const icon = $(this).find('i');
        
        if (passwordInput.attr('type') === 'password') {
            passwordInput.attr('type', 'text');
            icon.removeClass('fa-eye').addClass('fa-eye-slash');
        } else {
            passwordInput.attr('type', 'password');
            icon.removeClass('fa-eye-slash').addClass('fa-eye');
        }
    });

    $('.ajax-form').on('submit', function(e) {
        e.preventDefault();
        
        const form = $(this);
        const url = form.attr('action');
        const method = form.attr('method') || 'POST';
        const formData = new FormData(this);
        const originalButtonText = form.find('button[type="submit"]').html();
        
        $.ajax({
            url: url,
            type: method,
            data: formData,
            processData: false,
            contentType: false,
            beforeSend: function() {
                form.find('button[type="submit"]').prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang xử lý...');
            },
            success: function(response) {
                if (response.status === 'success') {
                    toastr.success(response.message);
                    
                    if (response.redirect) {
                        setTimeout(function() {
                            window.location.href = response.redirect;
                        }, 1500);
                    }
                    
                    if (response.reload) {
                        setTimeout(function() {
                            window.location.reload();
                        }, 1500);
                    }
                } else {
                    toastr.error(response.message || 'Đã xảy ra lỗi. Vui lòng thử lại sau.');
                }
            },
            error: function(xhr, status, error) {
                console.error(xhr.responseText);
                
                let errorMessage = 'Đã xảy ra lỗi. Vui lòng thử lại sau.';
                
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    errorMessage = xhr.responseJSON.message;
                }
                
                toastr.error(errorMessage);
            },
            complete: function() {
                form.find('button[type="submit"]').prop('disabled', false).html(originalButtonText);
            }
        });
    });

    $('a[data-bs-toggle="tab"]').on('shown.bs.tab', function(e) {
        localStorage.setItem('activeTab', $(e.target).attr('href'));
    });

    var activeTab = localStorage.getItem('activeTab');
    if (activeTab) {
        $('.nav-tabs a[href="' + activeTab + '"]').tab('show');
    }

    var hash = window.location.hash;
    if (hash) {
        $('.nav-tabs a[href="' + hash + '"]').tab('show');
    }

    window.addEventListener('popstate', function() {
        var hash = window.location.hash;
        if (hash) {
            $('.nav-tabs a[href="' + hash + '"]').tab('show');
        }
    });

    $('.image-preview-input').change(function() {
        const file = this.files[0];
        const fileReader = new FileReader();
        const preview = $(this).closest('.image-preview-container').find('.image-preview');
        
        if (file) {
            fileReader.onload = function() {
                preview.attr('src', fileReader.result);
            }
            fileReader.readAsDataURL(file);
            preview.removeClass('d-none');
        }
    });

    $('#vnpay-payment-form').on('submit', function(e) {
        e.preventDefault();
        
        const form = $(this);
        const amount = form.find('input[name="amount"]').val();
        
        if (!amount || parseFloat(amount) <= 0) {
            toastr.error('Vui lòng nhập số tiền hợp lệ');
            return;
        }
        
        form.submit();
    });


    $('.room-card').on('click', function() {
        const roomId = $(this).data('room-id');
        $('#selected-room-id').val(roomId);
        $('#room-registration-modal').modal('show');
    });


    $('.searchable-select').select2({
        theme: 'bootstrap-5',
        placeholder: 'Tìm kiếm...',
        allowClear: true
    });
    

    var clipboard = new ClipboardJS('.btn-copy');
    
    clipboard.on('success', function(e) {
        toastr.success('Đã sao chép vào clipboard');
        e.clearSelection();
    });
    
    clipboard.on('error', function(e) {
        toastr.error('Không thể sao chép. Vui lòng thử lại.');
    });

    $('.btn-print-invoice').on('click', function() {
        window.print();
    });

    $('.read-more-link').on('click', function(e) {
        e.preventDefault();
        $(this).closest('.read-more-container').find('.read-more-text').toggleClass('d-none');
        $(this).text($(this).text() === 'Xem thêm' ? 'Rút gọn' : 'Xem thêm');
    });
}

/**
 * Quản lý thông báo và alerts
 */
function initNotifications() {
    const alerts = document.querySelectorAll('.alert-auto-close');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert && bootstrap.Alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, 5000);
    });

    $('.toast').toast('show');

    updateNotifications();
    setInterval(updateNotifications, 60000);
}

/**
 * Cập nhật thông báo từ server mỗi phút
 */
function updateNotifications() {
    if (!document.getElementById('alertsDropdown')) return;
    
    fetch('/notification/api/update-notifications/')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const notificationBadge = document.querySelector('#alertsDropdown .badge');
                if (data.count > 0) {
                    if (notificationBadge) {
                        notificationBadge.textContent = data.count;
                        notificationBadge.classList.remove('d-none');
                    } else {
                        const badge = document.createElement('span');
                        badge.className = 'badge rounded-pill bg-danger';
                        badge.textContent = data.count;
                        document.querySelector('#alertsDropdown').appendChild(badge);
                    }
                } else if (notificationBadge) {
                    notificationBadge.classList.add('d-none');
                }

                const dropdownList = document.querySelector('.dropdown-list[aria-labelledby="alertsDropdown"]');
                if (dropdownList && data.notifications && data.notifications.length > 0) {
                    const notificationItems = dropdownList.querySelectorAll('.dropdown-item:not(.text-center)');
                    notificationItems.forEach(item => item.remove());
                    const header = dropdownList.querySelector('.dropdown-header');
                    if (header) {
                        data.notifications.forEach(notification => {
                            const item = document.createElement('a');
                            item.className = `dropdown-item d-flex align-items-center ${!notification.is_read ? 'fw-bold' : ''}`;
                            item.href = `/notification/detail/${notification.id}/`;
                            
                            item.innerHTML = `
                                <div class="me-3">
                                    <div class="icon-circle bg-${notification.color}">
                                        <i class="fas ${notification.icon} text-white"></i>
                                    </div>
                                </div>
                                <div>
                                    <div class="small text-gray-500">${notification.created_at}</div>
                                    <span class="${!notification.is_read ? 'fw-bold' : ''}">${notification.title}</span>
                                </div>
                            `;
                            
                            header.insertAdjacentElement('afterend', item);
                        });
                    }
                }
            }
        })
        .catch(error => console.error('Error updating notifications:', error));
}

/**
 * Khởi tạo các components đặc biệt
 */
function initSpecialComponents() {

}

/**
 * Khởi tạo các biểu đồ
 */
function initCharts() {
    var buildingChart = document.getElementById('buildingChart');
    if (buildingChart && typeof buildingLabels !== 'undefined' && typeof buildingData !== 'undefined') {
        new Chart(buildingChart, {
            type: 'bar',
            data: {
                labels: buildingLabels,
                datasets: [{
                    label: 'Số sinh viên',
                    data: buildingData,
                    backgroundColor: 'rgba(78, 115, 223, 0.8)',
                    borderColor: 'rgba(78, 115, 223, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    var revenueChart = document.getElementById('revenueChart');
    if (revenueChart && typeof monthLabels !== 'undefined' && typeof revenueData !== 'undefined') {
        new Chart(revenueChart, {
            type: 'line',
            data: {
                labels: monthLabels,
                datasets: [{
                    label: 'Doanh thu (VNĐ)',
                    data: revenueData,
                    backgroundColor: 'rgba(28, 200, 138, 0.1)',
                    borderColor: 'rgba(28, 200, 138, 1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString('vi-VN') + ' đ';
                            }
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + context.raw.toLocaleString('vi-VN') + ' đ';
                            }
                        }
                    }
                }
            }
        });
    }

    var roomStatusChart = document.getElementById('roomStatusChart');
    if (roomStatusChart && typeof roomStatusLabels !== 'undefined' && typeof roomStatusData !== 'undefined') {
        new Chart(roomStatusChart, {
            type: 'doughnut',
            data: {
                labels: roomStatusLabels,
                datasets: [{
                    data: roomStatusData,
                    backgroundColor: [
                        'rgba(28, 200, 138, 0.8)',
                        'rgba(246, 194, 62, 0.8)',
                        'rgba(231, 74, 59, 0.8)',
                        'rgba(54, 185, 204, 0.8)'
                    ],
                    borderColor: [
                        'rgba(28, 200, 138, 1)',
                        'rgba(246, 194, 62, 1)',
                        'rgba(231, 74, 59, 1)',
                        'rgba(54, 185, 204, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
}

/**
 * Tạo hóa đơn
 */
function createInvoice(userId, roomId, month, year) {
    $.ajax({
        url: '/payment/api/create-invoice/',
        type: 'POST',
        data: {
            user_id: userId,
            room_id: roomId,
            month: month,
            year: year,
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        },
        beforeSend: function() {
            $('.btn-create-invoice').prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang xử lý...');
        },
        success: function(response) {
            if (response.status === 'success') {
                toastr.success(response.message);
                setTimeout(function() {
                    window.location.href = response.redirect;
                }, 1000);
            } else {
                toastr.error(response.message);
            }
        },
        error: function() {
            toastr.error('Đã xảy ra lỗi. Vui lòng thử lại sau.');
        },
        complete: function() {
            $('.btn-create-invoice').prop('disabled', false).html('Tạo hóa đơn');
        }
    });
}

/**
 * Xử lý yêu cầu bảo trì
 */
function handleMaintenanceRequest(requestId, action, notes = '') {
    $.ajax({
        url: '/maintenance/api/handle-request/',
        type: 'POST',
        data: {
            request_id: requestId,
            action: action,
            notes: notes,
            csrfmiddlewaretoken: $('input[name="csrfmiddlewaretoken"]').val()
        },
        beforeSend: function() {
            $('.btn-handle-request').prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Đang xử lý...');
        },
        success: function(response) {
            if (response.status === 'success') {
                toastr.success(response.message);
                setTimeout(function() {
                    window.location.reload();
                }, 1000);
            } else {
                toastr.error(response.message);
            }
        },
        error: function() {
            toastr.error('Đã xảy ra lỗi. Vui lòng thử lại sau.');
        },
        complete: function() {
            $('.btn-handle-request').prop('disabled', false).html('Xử lý');
        }
    });
}

/**
 * Hiển thị thông báo
 */
function showNotification(type, message, title = '') {
    switch(type) {
        case 'success':
            toastr.success(message, title || 'Thành công');
            break;
        case 'error':
            toastr.error(message, title || 'Lỗi');
            break;
        case 'warning':
            toastr.warning(message, title || 'Cảnh báo');
            break;
        case 'info':
            toastr.info(message, title || 'Thông tin');
            break;
        default:
            toastr.info(message, title || 'Thông báo');
    }
}