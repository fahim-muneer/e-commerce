from django.urls import path

from .views import (
                    WalletDashboardView,
                    WithdrawalRequestView,
                    TransactionHistoryView,
                    AdminWalletDashboardView,
                    AdminWalletListView,
                    AdminWalletDetailView,
                    AdminAddMoneyView,
                    AdminDeductMoneyView,
                    AdminApproveWithdrawalView,
                    AdminRejectWithdrawalView,
                    AdminTransactionListView,
                    AdminWithdrawalRequestsView,
                    AddMoneyToWalletView,
                    VerifyWalletPaymentView,
                    SalesReportView,
                    ExportSalesReportCSV,
                    ExportSalesReportPDF,
                    ProductSalesReportView,


)
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('wallet_dashboard/',login_required(WalletDashboardView.as_view()),name="my_wallet"),
    path('withdraw/', login_required(WithdrawalRequestView.as_view()), name='wallet_withdrawal_request'),

    path('transactions/', login_required(TransactionHistoryView.as_view()), name='wallet_transaction_history'),

    
    path('wallet/', staff_member_required(AdminWalletDashboardView.as_view()), name='admin_wallet_dashboard'), #admn 
    path('wallet/list/', staff_member_required(AdminWalletListView.as_view()), name='admin_wallet_list'),#admn
    path('wallet/<int:wallet_id>/', staff_member_required(AdminWalletDetailView.as_view()), name='admin_wallet_detail'),#admn
    path('wallet/<int:wallet_id>/add-money/', staff_member_required(AdminAddMoneyView.as_view()), name='admin_add_money'),#admn
    path('wallet/<int:wallet_id>/deduct-money/', staff_member_required(AdminDeductMoneyView.as_view()), name='admin_deduct_money'),#admn
    path('wallet/withdrawals/', staff_member_required(AdminWithdrawalRequestsView.as_view()), name='admin_withdrawal_requests'), #admn
    path('wallet/withdrawals/<int:request_id>/approve/', staff_member_required(AdminApproveWithdrawalView.as_view()), name='admin_approve_withdrawal'),#admn
    path('wallet/withdrawals/<int:request_id>/reject/', staff_member_required(AdminRejectWithdrawalView.as_view()), name='admin_reject_withdrawal'),#admn
    path('wallet/transactions/', staff_member_required(AdminTransactionListView.as_view()), name='admin_transaction_list'),#admn
    path('add-money/', login_required(AddMoneyToWalletView.as_view()), name='wallet_add_money'),
    path('verify-payment/', login_required(VerifyWalletPaymentView.as_view()), name='wallet_verify_payment'),
    
    
    
    
    path('sales-report/', staff_member_required(SalesReportView.as_view()), name='sales_report'),#admn
    path('sales-report/export/csv/', staff_member_required(ExportSalesReportCSV.as_view()), name='export_sales_report_csv'),#admn
    path('sales-report/export/pdf/', staff_member_required(ExportSalesReportPDF.as_view()), name='export_sales_report_pdf'),#admin
    path('product-sales-report/', staff_member_required(ProductSalesReportView.as_view()), name='product_sales_report'),#admin


]
