from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from django.core.paginator import Paginator
from django.db import transaction
from decimal import Decimal
from .models import Wallet, WalletTransaction, WalletWithdrawalRequest
from customer.views import MyLoginRequiredMixin
from .models import Wallet, WalletTransaction, WalletWithdrawalRequest
from decimal import Decimal
from custom_admin.views import AdminLoginMixin
import razorpay
from django.conf import settings
from customer.models import Customer



from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncDate, TruncMonth, TruncYear
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
import csv
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.units import inch
from orders.models import Orders, OrderItem
from products.models import ProductPage
from customer.models import Register


razorpay_client = razorpay.Client(
    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
)

class AddMoneyToWalletView(MyLoginRequiredMixin, View):
    
    def get(self, request):
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        
        context = {
            'wallet': wallet,
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        }
        
        return render(request, 'wallet/add_money.html', context)
    
    def post(self, request):
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        
        try:
            amount = Decimal(request.POST.get('amount', '0'))
            
            # Validation
            if amount < 100:
                messages.error(request, 'Minimum amount to add is ₹100')
                return redirect('wallet_add_money')
            
            if amount > 50000:
                messages.error(request, 'Maximum amount to add is ₹50,000')
                return redirect('wallet_add_money')
            
            # Create Razorpay order
            razorpay_amount = int(amount * 100)  # Convert to paise
            
            razorpay_order = razorpay_client.order.create({
                'amount': razorpay_amount,
                'currency': 'INR',
                'payment_capture': '1'
            })
            
            context = {
                'wallet': wallet,
                'amount': amount,
                'razorpay_order_id': razorpay_order['id'],
                'razorpay_merchant_key': settings.RAZORPAY_KEY_ID,
                'razorpay_amount': razorpay_amount,
            }
            
            return render(request, 'wallet/add_money_payment.html', context)
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('wallet_add_money')


class VerifyWalletPaymentView(MyLoginRequiredMixin, View):
    """Verify Razorpay payment and credit wallet"""
    
    @transaction.atomic
    def post(self, request):
        
        wallet = get_object_or_404(Wallet, user=request.user)
        
        razorpay_payment_id = request.POST.get('razorpay_payment_id', '').strip()
        razorpay_order_id = request.POST.get('razorpay_order_id', '').strip()
        razorpay_signature = request.POST.get('razorpay_signature', '').strip()
        amount_str = request.POST.get('amount', '0')
        

        try:
            amount = Decimal(amount_str)
            
            if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
                messages.error(request, 'Payment details are incomplete.')
                return redirect('wallet_add_money')
            
            # Verify signature
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            
            print("Verifying payment signature...")
            razorpay_client.utility.verify_payment_signature(params_dict)
            
            # Add money to wallet
            print(f"Adding ₹{amount} to wallet...")
            transaction = wallet.add_money(
                amount=amount,
                transaction_type=WalletTransaction.CREDIT_ADMIN,
                description=f"Added via Razorpay - Payment ID: {razorpay_payment_id}",
                reference_id=razorpay_payment_id
            )
            
            
            messages.success(request, f'₹{amount} added to your wallet successfully!')
            return redirect('my_wallet')
            
        except ValueError as e:
            messages.error(request, f'Invalid amount: {str(e)}')
            return redirect('wallet_add_money')
        except Exception as e:
            import traceback
            traceback.print_exc()
            messages.error(request, 'Payment verification failed. Please contact support.')
            return redirect('wallet_add_money')


class WalletDashboardView(MyLoginRequiredMixin, View):
    """User's wallet dashboard"""
    
    def get(self, request):
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        
        transactions = WalletTransaction.objects.filter(
            wallet=wallet
        ).order_by('-created_at')
        
        page = request.GET.get('page', 1)
        paginator = Paginator(transactions, 10)
        transactions = paginator.get_page(page)
        
        total_credits = WalletTransaction.objects.filter(
            wallet=wallet,
            transaction_type__startswith='credit'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        total_debits = WalletTransaction.objects.filter(
            wallet=wallet,
            transaction_type__startswith='debit'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        pending_withdrawals = WalletWithdrawalRequest.objects.filter(
            wallet=wallet,
            status=WalletWithdrawalRequest.PENDING
        )
        print("the profile picture process starts here")
        profile = Customer.objects.get(user=request.user) #pylint: disable=no-member
        print("the profile picture is updated ")

        
        context = {
            'profie':profile,
            'wallet': wallet,
            'transactions': transactions,
            'total_credits': total_credits,
            'total_debits': total_debits,
            'pending_withdrawals': pending_withdrawals,
        }
        
        return render(request, 'wallet/my_wallet.html', context)


class WithdrawalRequestView(MyLoginRequiredMixin, View):
    """User creates withdrawal request"""
    
    def get(self, request):
        wallet = get_object_or_404(Wallet, user=request.user)
        
        # Get pending requests
        pending_requests = WalletWithdrawalRequest.objects.filter(
            wallet=wallet,
            status=WalletWithdrawalRequest.PENDING
        )
        
        context = {
            'wallet': wallet,
            'pending_requests': pending_requests,
        }
        
        return render(request, 'wallet/withdrawal_request.html', context)
    
    def post(self, request):
        wallet = get_object_or_404(Wallet, user=request.user)
        
        try:
            amount = Decimal(request.POST.get('amount', '0'))
            account_holder_name = request.POST.get('account_holder_name', '').strip()
            account_number = request.POST.get('account_number', '').strip()
            ifsc_code = request.POST.get('ifsc_code', '').strip()
            bank_name = request.POST.get('bank_name', '').strip()
            
            # Validation
            if amount <= 0:
                messages.error(request, 'Please enter a valid amount')
                return redirect('wallet_withdrawal_request')
            
            if amount < 100:
                messages.error(request, 'Minimum withdrawal amount is ₹100')
                return redirect('wallet_withdrawal_request')
            
            if not wallet.has_sufficient_balance(amount):
                messages.error(request, 'Insufficient wallet balance')
                return redirect('wallet_withdrawal_request')
            
            if not all([account_holder_name, account_number, ifsc_code, bank_name]):
                messages.error(request, 'Please fill all bank details')
                return redirect('wallet_withdrawal_request')
            
            # Check for pending requests
            pending_count = WalletWithdrawalRequest.objects.filter(
                wallet=wallet,
                status=WalletWithdrawalRequest.PENDING
            ).count()
            
            if pending_count >= 3:
                messages.error(request, 'You already have 3 pending withdrawal requests. Please wait for them to be processed.')
                return redirect('wallet_withdrawal_request')
            
            # Create withdrawal request
            withdrawal = WalletWithdrawalRequest.objects.create(
                wallet=wallet,
                amount=amount,
                account_holder_name=account_holder_name,
                account_number=account_number,
                ifsc_code=ifsc_code,
                bank_name=bank_name
            )
            
            messages.success(request, f'Withdrawal request for ₹{amount} submitted successfully. Request ID: {withdrawal.request_id}')
            return redirect('wallet_dashboard')
            
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('wallet_withdrawal_request')
        except Exception as e:
            messages.error(request, f'Error creating withdrawal request: {str(e)}')
            return redirect('wallet_withdrawal_request')


class TransactionHistoryView(MyLoginRequiredMixin, View):
    """View detailed transaction history"""
    
    def get(self, request):
        wallet = get_object_or_404(Wallet, user=request.user)
        
        # Filters
        transaction_type = request.GET.get('type', '')
        start_date = request.GET.get('start_date', '')
        end_date = request.GET.get('end_date', '')
        
        transactions = WalletTransaction.objects.filter(wallet=wallet)
        
        # Apply filters
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)
        
        if start_date:
            from datetime import datetime
            start = datetime.strptime(start_date, '%Y-%m-%d')
            transactions = transactions.filter(created_at__gte=start)
        
        if end_date:
            from datetime import datetime
            end = datetime.strptime(end_date, '%Y-%m-%d')
            transactions = transactions.filter(created_at__lte=end)
        
        transactions = transactions.order_by('-created_at')
        
        # Pagination
        page = request.GET.get('page', 1)
        paginator = Paginator(transactions, 20)
        transactions = paginator.get_page(page)
        
        context = {
            'wallet': wallet,
            'transactions': transactions,
            'transaction_type': transaction_type,
            'start_date': start_date,
            'end_date': end_date,
        }
        
        return render(request, 'wallet/transaction_history.html', context)


def apply_wallet_to_order(user, order_total):
    """Apply wallet balance to reduce order total"""
    try:
        wallet = Wallet.objects.get(user=user)
        
        if wallet.balance > 0:
            # Calculate how much wallet balance to use
            wallet_amount_used = min(wallet.balance, Decimal(str(order_total)))
            
            # Deduct from wallet
            wallet.deduct_money(
                amount=wallet_amount_used,
                transaction_type=WalletTransaction.DEBIT_PURCHASE,
                description=f"Payment for order",
                reference_id=None  # Add order ID later
            )
            
            # Calculate remaining amount to pay
            remaining_amount = Decimal(str(order_total)) - wallet_amount_used
            
            return {
                'wallet_used': wallet_amount_used,
                'remaining_amount': remaining_amount,
                'success': True
            }
    except Wallet.DoesNotExist:
        pass
    
    return {
        'wallet_used': Decimal('0'),
        'remaining_amount': Decimal(str(order_total)),
        'success': False
    }



def credit_refund_to_wallet(user, amount, order_id):
    """Credit refund to user's wallet"""
    wallet, created = Wallet.objects.get_or_create(user=user)
    return wallet.add_money(
        amount=amount,
        transaction_type=WalletTransaction.CREDIT_REFUND,
        description=f"Refund for order #{order_id}",
        reference_id=order_id
    )


def credit_cashback_to_wallet(user, amount, order_id):
    """Credit cashback to user's wallet"""
    wallet, created = Wallet.objects.get_or_create(user=user)
    return wallet.add_money(
        amount=amount,
        transaction_type=WalletTransaction.CREDIT_CASHBACK,
        description=f"Cashback for order #{order_id}",
        reference_id=order_id
    )


def credit_referral_bonus_to_wallet(user, amount, referral_id):
    """Credit referral bonus to user's wallet"""
    wallet, created = Wallet.objects.get_or_create(user=user)
    return wallet.add_money(
        amount=amount,
        transaction_type=WalletTransaction.CREDIT_REFERRAL,
        description=f"Referral bonus",
        reference_id=str(referral_id)
    )
    










class AdminWalletDashboardView(AdminLoginMixin, View):
    """Admin dashboard for wallet system"""
    
    def get(self, request):
        # Overall statistics
        total_wallets = Wallet.objects.count()
        total_balance = Wallet.objects.aggregate(
            total=Sum('balance')
        )['total'] or Decimal('0')
        
        active_wallets = Wallet.objects.filter(balance__gt=0).count()
        
        # Transaction statistics
        total_transactions = WalletTransaction.objects.count()
        total_credits = WalletTransaction.objects.filter(
            transaction_type__startswith='credit'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
         
        total_debits = WalletTransaction.objects.filter(
            transaction_type__startswith='debit'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Withdrawal statistics
        pending_withdrawals = WalletWithdrawalRequest.objects.filter(
            status=WalletWithdrawalRequest.PENDING
        ).count()
        
        pending_amount = WalletWithdrawalRequest.objects.filter(
            status=WalletWithdrawalRequest.PENDING
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Recent transactions
        recent_transactions = WalletTransaction.objects.select_related(
            'wallet__user'
        ).order_by('-created_at')[:10]
        
        # Top wallets
        top_wallets = Wallet.objects.select_related('user').order_by('-balance')[:10]
        
        context = {
            'stats': {
                'total_wallets': total_wallets,
                'total_balance': total_balance,
                'active_wallets': active_wallets,
                'total_transactions': total_transactions,
                'total_credits': total_credits,
                'total_debits': total_debits,
                'pending_withdrawals': pending_withdrawals,
                'pending_amount': pending_amount,
            },
            'recent_transactions': recent_transactions,
            'top_wallets': top_wallets,
        }
        
        return render(request, 'wallet/admin_wallet_dashboard.html', context)


class AdminWalletListView(AdminLoginMixin, View):
    """List all user wallets"""
    
    def get(self, request):
        search = request.GET.get('search', '')
        balance_filter = request.GET.get('balance', '')
        
        wallets = Wallet.objects.select_related('user').all()
        
        # Apply filters
        if search:
            wallets = wallets.filter(
                Q(user__email__icontains=search) |
                Q(user__full_name__icontains=search)
            )
        
        if balance_filter == 'positive':
            wallets = wallets.filter(balance__gt=0)
        elif balance_filter == 'zero':
            wallets = wallets.filter(balance=0)
        
        wallets = wallets.order_by('-balance')
        
        # Pagination
        page = request.GET.get('page', 1)
        paginator = Paginator(wallets, 20)
        wallets = paginator.get_page(page)
        
        context = {
            'wallets': wallets,
            'search': search,
            'balance_filter': balance_filter,
        }
        
        return render(request, 'wallet/admin_wallet_list.html', context)


class AdminWalletDetailView(AdminLoginMixin, View):
    """View detailed wallet information"""
    
    def get(self, request, wallet_id):
        wallet = get_object_or_404(Wallet, pk=wallet_id)
        
        # Get transactions
        transactions = WalletTransaction.objects.filter(
            wallet=wallet
        ).order_by('-created_at')
        
        # Pagination
        page = request.GET.get('page', 1)
        paginator = Paginator(transactions, 20)
        transactions = paginator.get_page(page)
        
        # Statistics
        from django.db.models import Sum
        total_credits = WalletTransaction.objects.filter(
            wallet=wallet,
            transaction_type__startswith='credit'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        total_debits = WalletTransaction.objects.filter(
            wallet=wallet,
            transaction_type__startswith='debit'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Withdrawal requests
        withdrawal_requests = WalletWithdrawalRequest.objects.filter(
            wallet=wallet
        ).order_by('-requested_at')
        
        context = {
            'wallet': wallet,
            'transactions': transactions,
            'total_credits': total_credits,
            'total_debits': total_debits,
            'withdrawal_requests': withdrawal_requests,
        }
        
        return render(request, 'wallet/admin_wallet_detail.html', context)


class AdminAddMoneyView(AdminLoginMixin, View):
    """Admin adds money to user wallet"""
    
    def post(self, request, wallet_id):
        wallet = get_object_or_404(Wallet, pk=wallet_id)
        
        try:
            amount = Decimal(request.POST.get('amount', '0'))
            description = request.POST.get('description', 'Admin credit')
            
            if amount <= 0:
                messages.error(request, 'Amount must be positive')
                return redirect('admin_wallet_detail', wallet_id=wallet_id)
            
            # Add money
            wallet.add_money(
                amount=amount,
                transaction_type=WalletTransaction.CREDIT_ADMIN,
                description=f"{description} (by {request.user.email})",
                reference_id=None
            )
            
            messages.success(request, f'₹{amount} added to {wallet.user.email} wallet')
            return redirect('admin_wallet_detail', wallet_id=wallet_id)
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('admin_wallet_detail', wallet_id=wallet_id)


class AdminDeductMoneyView(AdminLoginMixin, View):
    """Admin deducts money from user wallet"""
    
    def post(self, request, wallet_id):
        wallet = get_object_or_404(Wallet, pk=wallet_id)
        
        try:
            amount = Decimal(request.POST.get('amount', '0'))
            description = request.POST.get('description', 'Admin debit')
            
            if amount <= 0:
                messages.error(request, 'Amount must be positive')
                return redirect('admin_wallet_detail', wallet_id=wallet_id)
            
            # Deduct money
            wallet.deduct_money(
                amount=amount,
                transaction_type=WalletTransaction.DEBIT_ADMIN,
                description=f"{description} (by {request.user.email})",
                reference_id=None
            )
            
            messages.success(request, f'₹{amount} deducted from {wallet.user.email} wallet')
            return redirect('admin_wallet_detail', wallet_id=wallet_id)
            
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('admin_wallet_detail', wallet_id=wallet_id)
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('admin_wallet_detail', wallet_id=wallet_id)


class AdminWithdrawalRequestsView(AdminLoginMixin, View):
    """Manage withdrawal requests"""
    
    def get(self, request):
        status_filter = request.GET.get('status', 'pending')
        
        requests = WalletWithdrawalRequest.objects.select_related(
            'wallet__user'
        ).all()
        
        if status_filter:
            requests = requests.filter(status=status_filter)
        
        requests = requests.order_by('-requested_at')
        
        # Pagination
        page = request.GET.get('page', 1)
        paginator = Paginator(requests, 10)
        requests = paginator.get_page(page)
        
        context = {
            'requests': requests,
            'status_filter': status_filter,
        }
        
        return render(request, 'wallet/admin_withdrawal_requests.html', context)


class AdminApproveWithdrawalView(AdminLoginMixin, View):
    """Approve withdrawal request"""   
    
    def post(self, request, request_id):
        withdrawal = get_object_or_404(WalletWithdrawalRequest, pk=request_id)
        print(f"post request from {withdrawal}")
        remarks = request.POST.get('remarks', '')
        print(f"")
        
        try:
            withdrawal.approve(admin_user=request.user, remarks=remarks)
            messages.success(request, f'Withdrawal request {withdrawal.request_id} approved and processed')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        
        return redirect('admin_withdrawal_requests')


class AdminRejectWithdrawalView(AdminLoginMixin, View):
    """Reject withdrawal request"""
    
    def post(self, request, request_id):
        withdrawal = get_object_or_404(WalletWithdrawalRequest, pk=request_id)
        remarks = request.POST.get('remarks', '')
        
        if not remarks:
            messages.error(request, 'Please provide reason for rejection')
            return redirect('admin_withdrawal_requests')
        
        try:
            withdrawal.reject(admin_user=request.user, remarks=remarks)
            messages.success(request, f'Withdrawal request {withdrawal.request_id} rejected')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        
        return redirect('admin_withdrawal_requests')


class AdminTransactionListView(AdminLoginMixin, View):
    """View all wallet transactions"""
    
    def get(self, request):
        search = request.GET.get('search', '')
        transaction_type = request.GET.get('type', '')
        
        transactions = WalletTransaction.objects.select_related(
            'wallet__user'
        ).all()
        
        if search:
            transactions = transactions.filter(
                Q(wallet__user__email__icontains=search) |
                Q(transaction_id__icontains=search) |
                Q(reference_id__icontains=search)
            )
        
        if transaction_type:
            transactions = transactions.filter(transaction_type=transaction_type)
        
        transactions = transactions.order_by('-created_at')
        
        # Pagination
        page = request.GET.get('page', 1)
        paginator = Paginator(transactions, 30)
        transactions = paginator.get_page(page)
        
        context = {
            'transactions': transactions,
            'search': search,
            'transaction_type': transaction_type,
        }
        
        return render(request, 'admin_panel/wallet/transactions.html', context)
    
    
class SalesReportView(AdminLoginMixin, View):
    """Main Sales Report Dashboard"""
    
    def get(self, request):
        # Get filter parameters
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        period = request.GET.get('period', 'all')  # daily, weekly, monthly, yearly, custom, all
        payment_method = request.GET.get('payment_method', '')
        order_status = request.GET.get('order_status', '')
        
        # Base queryset - only confirmed and delivered orders
        orders = Orders.objects.filter(
            order_status__in=[Orders.STATUS_CONFIRMED, Orders.STATUS_PROCESSED, Orders.STATUS_DELIVERED]
        )
        
        # Apply date filters based on period
        now = timezone.now()
        if period == 'daily':
            start_date = now.date()
            end_date = now.date()
        elif period == 'weekly':
            start_date = (now - timedelta(days=7)).date()
            end_date = now.date()
        elif period == 'monthly':
            start_date = (now - timedelta(days=30)).date()
            end_date = now.date()
        elif period == 'yearly':
            start_date = (now - timedelta(days=365)).date()
            end_date = now.date()
        elif period == 'custom':
            if start_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Apply date range filter
        if start_date and end_date:
            orders = orders.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
        elif start_date:
            orders = orders.filter(created_at__date__gte=start_date)
        elif end_date:
            orders = orders.filter(created_at__date__lte=end_date)
        
        # Apply additional filters
        if payment_method:
            orders = orders.filter(payment_method=payment_method)
        
        if order_status:
            orders = orders.filter(order_status=order_status)
        
        # Calculate overall statistics
        total_orders = orders.count()
        total_revenue = orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        # Calculate average order value
        avg_order_value = orders.aggregate(avg=Avg('total_amount'))['avg'] or Decimal('0')
        
        # Payment method breakdown
        payment_breakdown = orders.values('payment_method').annotate(
            count=Count('id'),
            total=Sum('total_amount')
        )
        
        # Order status breakdown
        status_breakdown = orders.values('order_status').annotate(
            count=Count('id'),
            total=Sum('total_amount')
        )
        
        # Top selling products
        top_products = OrderItem.objects.filter(
            order__in=orders
        ).values(
            'product__name',
            'product__id'
        ).annotate(
            quantity_sold=Sum('quantity'),
            revenue=Sum(F('quantity') * F('unit_price'))
        ).order_by('-quantity_sold')[:10]
        
        # Daily sales trend (for chart)
        daily_sales = orders.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('date')
        
        # Top customers
        top_customers = orders.values(
            'user__full_name',
            'user__email'
        ).annotate(
            total_spent=Sum('total_amount'),
            order_count=Count('id')
        ).order_by('-total_spent')[:10]
        
        # Pagination for order list
        page = request.GET.get('page', 1)
        paginator = Paginator(orders.order_by('-created_at'), 20)
        orders_page = paginator.get_page(page)
        
        context = {
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'avg_order_value': avg_order_value,
            'payment_breakdown': payment_breakdown,
            'status_breakdown': status_breakdown,
            'top_products': top_products,
            'daily_sales': list(daily_sales),
            'top_customers': top_customers,
            'orders': orders_page,
            'start_date': start_date,
            'end_date': end_date,
            'period': period,
            'payment_method': payment_method,
            'order_status': order_status,
            'payment_choices': Orders.PAYMENT_CHOICES,
            'status_choices': Orders.STATUS_CHOICES,
        }
        
        return render(request, 'wallet/sales_report.html', context)


class ExportSalesReportCSV(AdminLoginMixin, View):
    """Export Sales Report as CSV"""
    
    def get(self, request):
        # Get same filters as main report
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        payment_method = request.GET.get('payment_method', '')
        order_status = request.GET.get('order_status', '')
        
        # Get filtered orders
        orders = Orders.objects.filter(
            order_status__in=[Orders.STATUS_CONFIRMED, Orders.STATUS_PROCESSED, Orders.STATUS_DELIVERED]
        )
        
        if start_date:
            orders = orders.filter(created_at__date__gte=datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            orders = orders.filter(created_at__date__lte=datetime.strptime(end_date, '%Y-%m-%d').date())
        if payment_method:
            orders = orders.filter(payment_method=payment_method)
        if order_status:
            orders = orders.filter(order_status=order_status)
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="sales_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow([
            'Order ID',
            'Date',
            'Customer Name',
            'Customer Email',
            'Payment Method',
            'Order Status',
            'Total Amount',
            'Items Count'
        ])
        
        # Write data
        for order in orders:
            writer.writerow([
                order.order_Id,
                order.created_at.strftime('%Y-%m-%d %H:%M'),
                order.user.full_name if order.user else 'N/A',
                order.user.email if order.user else 'N/A',
                order.get_payment_method_display(),
                order.get_order_status_display(),
                order.total_amount,
                order.items.count()
            ])
        
        # Write summary
        writer.writerow([])
        writer.writerow(['Summary'])
        writer.writerow(['Total Orders', orders.count()])
        writer.writerow(['Total Revenue', orders.aggregate(total=Sum('total_amount'))['total'] or 0])
        writer.writerow(['Average Order Value', orders.aggregate(avg=Avg('total_amount'))['avg'] or 0])
        
        return response


class ExportSalesReportPDF(AdminLoginMixin, View):
    """Export Sales Report as PDF"""
    
    def get(self, request):
        # Get same filters
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        payment_method = request.GET.get('payment_method', '')
        order_status = request.GET.get('order_status', '')
        
        # Get filtered orders
        orders = Orders.objects.filter(
            order_status__in=[Orders.STATUS_CONFIRMED, Orders.STATUS_PROCESSED, Orders.STATUS_DELIVERED]
        )
        
        if start_date:
            orders = orders.filter(created_at__date__gte=datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            orders = orders.filter(created_at__date__lte=datetime.strptime(end_date, '%Y-%m-%d').date())
        if payment_method:
            orders = orders.filter(payment_method=payment_method)
        if order_status:
            orders = orders.filter(order_status=order_status)
        
        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a202c'),
            spaceAfter=30,
            alignment=1  # Center
        )
        story.append(Paragraph("Sales Report", title_style))
        
        # Date range
        if start_date or end_date:
            date_text = f"Period: {start_date or 'Start'} to {end_date or 'End'}"
            story.append(Paragraph(date_text, styles['Normal']))
        
        story.append(Spacer(1, 20))
        
        # Summary statistics
        total_orders = orders.count()
        total_revenue = orders.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        avg_order = orders.aggregate(avg=Avg('total_amount'))['avg'] or Decimal('0')
        
        summary_data = [
            ['Metric', 'Value'],
            ['Total Orders', str(total_orders)],
            ['Total Revenue', f'₹{total_revenue:,.2f}'],
            ['Average Order Value', f'₹{avg_order:,.2f}'],
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 30))
        
        # Orders table
        story.append(Paragraph("Order Details", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        order_data = [['Order ID', 'Date', 'Customer', 'Payment', 'Status', 'Amount']]
        
        for order in orders[:50]:  # Limit to 50 orders for PDF
            order_data.append([
                str(order.order_Id)[:8],
                order.created_at.strftime('%Y-%m-%d'),
                order.user.full_name[:20] if order.user else 'N/A',
                order.get_payment_method_display()[:10],
                order.get_order_status_display()[:10],
                f'₹{order.total_amount:,.2f}'
            ])
        
        order_table = Table(order_data, colWidths=[1.2*inch, 1*inch, 1.8*inch, 1.2*inch, 1.2*inch, 1*inch])
        order_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        
        story.append(order_table)
        
        if orders.count() > 50:
            story.append(Spacer(1, 10))
            story.append(Paragraph(f"Showing 50 of {orders.count()} orders", styles['Italic']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="sales_report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
        
        return response


class ProductSalesReportView(AdminLoginMixin, View):
    """Detailed Product Sales Report"""
    
    def get(self, request):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        # Base queryset
        order_items = OrderItem.objects.filter(
            order__order_status__in=[Orders.STATUS_CONFIRMED, Orders.STATUS_PROCESSED, Orders.STATUS_DELIVERED]
        )
        
        # Apply date filters
        if start_date:
            order_items = order_items.filter(order__created_at__date__gte=datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            order_items = order_items.filter(order__created_at__date__lte=datetime.strptime(end_date, '%Y-%m-%d').date())
        
        # Product-wise sales
        product_sales = order_items.values(
            'product__id',
            'product__name',
            'product__category__name'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('unit_price')),
            order_count=Count('order', distinct=True)
        ).order_by('-total_revenue')
        
        # Pagination
        page = request.GET.get('page', 1)
        paginator = Paginator(product_sales, 20)
        products_page = paginator.get_page(page)
        
        context = {
            'products': products_page,
            'start_date': start_date,
            'end_date': end_date,
        }
        
        return render(request, 'admin_panel/reports/product_sales_report.html', context)