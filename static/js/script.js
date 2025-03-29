
$(document).ready(function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    $("#sidebarToggle").on("click", function(e) {
        e.preventDefault();
        $("body").toggleClass("sidebar-toggled");
        $(".sidebar").toggleClass("toggled");
        if ($(".sidebar").hasClass("toggled")) {
            $('.sidebar .collapse').collapse('hide');
        }
    });

    $(window).resize(function() {
        if ($(window).width() < 768) {
            $('.sidebar .collapse').collapse('hide');
        }
        if ($(window).width() < 480 && !$(".sidebar").hasClass("toggled")) {
            $("body").addClass("sidebar-toggled");
            $(".sidebar").addClass("toggled");
            $('.sidebar .collapse').collapse('hide');
        }
    });

    if ($(window).width() < 768) {
        $('.sidebar .collapse').collapse('hide');
    }

    $(window).scroll(function() {
        if ($(this).scrollTop() > 100) {
            $('.scroll-to-top').fadeIn();
        } else {
            $('.scroll-to-top').fadeOut();
        }
    });

    $('.scroll-to-top').click(function() {
        $('html, body').animate({scrollTop : 0}, 800);
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

    setTimeout(function() {
        $('.alert-auto-close').alert('close');
    }, 5000);
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

    $('.toast').toast('show');

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
                form.find('button[type="submit"]').prop('disabled', false).html(form.find('button[type="submit"]').data('original-text') || 'Gửi');
            }
        });
    });

    $('a[data-bs-toggle="tab"]').on('shown.bs.tab', function (e) {
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

    // Xử lý đăng ký phòng
    $('.room-card').on('click', function() {
        const roomId = $(this).data('room-id');
        $('#selected-room-id').val(roomId);
        $('#room-registration-modal').modal('show');
    });

    // Hiện danh sách có thể tìm kiếm
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

    if ($('#myChart').length > 0) {
        initCharts();
    }
    $('.read-more-link').on('click', function(e) {
        e.preventDefault();
        $(this).closest('.read-more-container').find('.read-more-text').toggleClass('d-none');
        $(this).text($(this).text() === 'Xem thêm' ? 'Rút gọn' : 'Xem thêm');
    });
});

function initCharts() {

    var buildingChart = document.getElementById('buildingChart');
    if (buildingChart) {
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
    if (revenueChart) {
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
    if (roomStatusChart) {
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

function createInvoice(userId, roomId, month, year) {
    $.ajax({
        url: '/payment/create-invoice/',
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

function handleMaintenanceRequest(requestId, action, notes = '') {
    $.ajax({
        url: '/maintenance/handle-request/',
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