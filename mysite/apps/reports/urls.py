from django.urls import path
from apps.reports.views.daybook import daybook, daybook_calc_opening_closing
from apps.reports.views.item_wise_profit_and_loss import item_wise_profit_and_loss
from apps.reports.views.bill_wise_profit_and_loss import bill_wise_profit_and_loss
from apps.reports.views.quotation_book import quotation_book
from apps.reports.views.comprehensive_sale import comprehensive_sale
from apps.reports.views.accounts_receivable import accounts_receivable
from apps.reports.views.accounts_payable import accounts_payable
from apps.reports.views.stock_report import stock_report

from . import render_to_pdf , render_to_excell
from apps.reports.views.urdu_names import urdu_name_suggestions
from apps.reports.views.inventory_update import inventory_update



urlpatterns = [
    path('daybook/', daybook, name='daybook'),
    path('item-wise-profit-and-loss/', item_wise_profit_and_loss, name='item_wise_profit_and_loss'),
    path('bill-wise-profit-and-loss/', bill_wise_profit_and_loss, name='bill_wise_profit_and_loss'),
    path('quotation-book/', quotation_book, name='quotation_book'),
    path('comprehensive-sale/', comprehensive_sale, name='comprehensive_sale'),
    path('accounts-receivable/', accounts_receivable, name='accounts_receivable'),
    path('accounts-payable/', accounts_payable, name='accounts_payable'),
    path('stock-report/', stock_report, name='stock_report'),
    
    path('daybook/calc-opening-closing/', daybook_calc_opening_closing, name='daybook_calc_opening_closing'),
    path('inventory-update/', inventory_update, name='inventory_update'),
    path('inventory-update/urdu-suggestions/', urdu_name_suggestions, name='urdu_name_suggestions'),


]
