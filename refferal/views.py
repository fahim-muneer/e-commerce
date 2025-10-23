from django.shortcuts import render, redirect, get_object_or_404
from customer.models import Referral, ReferralReward, ReferralCode
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views import View 
from customer.views import MyLoginRequiredMixin
from customer.models import Register, Customer
from django.utils import timezone
from django.db.models import Q, Count, Sum
from custom_admin.views import AdminLoginMixin
from django.core.paginator import Paginator
from offer.models import Offers
from decimal import Decimal


@method_decorator(never_cache, name='dispatch')
class ReferralDashboard(MyLoginRequiredMixin, View):
    """User's referral dashboard"""
    
    def get(self, request):
        user = request.user
        
        # Get or create referral code
        referral_code_obj, created = ReferralCode.objects.get_or_create(
            user=user,
            defaults={'code': ReferralCode.generate_unique_code(user)}
        )
        
        # Get referrals made by this user
        referrals_made = Referral.objects.filter(
            referrer=user
        ).select_related('referred').order_by('-signed_up_at')
        
        # Get available rewards
        available_rewards = ReferralReward.objects.filter(
            user=user,
            is_used=False,
            valid_from__lte=timezone.now(),
            valid_until__gte=timezone.now()
        ).select_related('offer')
        
        # Get used rewards
        used_rewards = ReferralReward.objects.filter(
            user=user,
            is_used=True
        ).select_related('offer', 'order').order_by('-used_at')
        
        # Build referral URL
        referral_url = request.build_absolute_uri(
            f'/customer/signup/?ref={referral_code_obj.code}'
        )
        
        # Calculate stats
        try:
            register = Register.objects.get(email=user.email)
            total_earnings = register.total_referral_earnings or Decimal('0')
            successful_referrals = register.successful_referrals_count or 0
        except Register.DoesNotExist:
            total_earnings = Decimal('0')
            successful_referrals = 0
        
        # Get profile for sidebar
        try:
            profile = Customer.objects.get(user=request.user)
        except Customer.DoesNotExist:
            profile = None
        
        # Count pending referrals (signed up but no purchase yet)
        pending_referrals = referrals_made.filter(
            first_purchase_at__isnull=True
        ).count()
        
        context = {
            'profile': profile,
            'referral_code': referral_code_obj.code,
            'referral_url': referral_url,
            'referrals_made': referrals_made,
            'available_rewards': available_rewards,
            'used_rewards': used_rewards,
            'total_earnings': total_earnings,
            'successful_referrals': successful_referrals,
            'pending_referrals': pending_referrals,
        }
        
        return render(request, 'refferals/referral_dashboard.html', context)


class ReferralDashboardView(AdminLoginMixin, View):
    """Admin referral dashboard"""
    
    def get(self, request):
        # Overall statistics
        total_referrals = Referral.objects.count()
        successful_referrals = Referral.objects.filter(
            first_purchase_at__isnull=False
        ).count()
        pending_referrals = total_referrals - successful_referrals
        
        # Calculate conversion rate safely
        conversion_rate = 0
        if total_referrals > 0:
            conversion_rate = (successful_referrals / total_referrals) * 100
        
        # Reward statistics
        total_rewards = ReferralReward.objects.count()
        used_rewards = ReferralReward.objects.filter(is_used=True).count()
        available_rewards = total_rewards - used_rewards
        
        total_discount_given = ReferralReward.objects.filter(
            is_used=True
        ).aggregate(total=Sum('discount_amount'))['total'] or Decimal('0')
        
        # Top referrers
        top_referrers = Referral.objects.values(
            'referrer__email', 
            'referrer__full_name'
        ).annotate(
            referral_count=Count('id'),
            successful_count=Count(
                'id', 
                filter=Q(first_purchase_at__isnull=False)
            )
        ).order_by('-referral_count')[:10]
        
        # Recent referrals
        recent_referrals = Referral.objects.select_related(
            'referrer', 'referred'
        ).order_by('-signed_up_at')[:10]
        
        # Active referral offers
        now = timezone.now()
        active_offers = Offers.objects.filter(
            offer_type='referral',
            active=True,
            start_date__lte=now,
            end_date__gte=now
        )
        
        context = {
            'stats': {
                'total_referrals': total_referrals,
                'successful_referrals': successful_referrals,
                'pending_referrals': pending_referrals,
                'conversion_rate': round(conversion_rate, 1),
                'total_rewards': total_rewards,
                'used_rewards': used_rewards,
                'available_rewards': available_rewards,
                'total_discount_given': total_discount_given,
            },
            'top_referrers': top_referrers,
            'recent_referrals': recent_referrals,
            'active_offers': active_offers,
        }
        
        return render(request, 'refferals/refferal_admin_dashboard.html', context)


class ReferralListView(AdminLoginMixin, View):
    """List all referrals with filters - admin side"""
    
    def get(self, request):
        search = request.GET.get('search', '').strip()
        status_filter = request.GET.get('status', '')
        
        # Base queryset
        referrals = Referral.objects.select_related(
            'referrer', 'referred', 'referral_code'
        ).order_by('-signed_up_at')
        
        # Apply search filter
        if search:
            referrals = referrals.filter(
                Q(referrer__email__icontains=search) |
                Q(referrer__full_name__icontains=search) |
                Q(referred__email__icontains=search) |
                Q(referred__full_name__icontains=search) |
                Q(referral_code__code__icontains=search)
            )
        
        # Apply status filter
        if status_filter == 'pending':
            referrals = referrals.filter(first_purchase_at__isnull=True)
        elif status_filter == 'completed':
            referrals = referrals.filter(first_purchase_at__isnull=False)
        elif status_filter == 'rewarded':
            referrals = referrals.filter(status=Referral.BOTH_REWARDED)
        
        # Pagination
        page = request.GET.get('page', 1)
        paginator = Paginator(referrals, 20)
        referrals_page = paginator.get_page(page)
        
        context = {
            'referrals': referrals_page,
            'search': search,
            'status_filter': status_filter,
        }
        
        return render(request, 'admin_panel/referrals/list.html', context)


class ReferralRewardListView(AdminLoginMixin, View):
    """List all referral rewards"""
    
    def get(self, request):
        search = request.GET.get('search', '').strip()
        status_filter = request.GET.get('status', '')
        reward_type = request.GET.get('type', '')
        
        # Base queryset
        rewards = ReferralReward.objects.select_related(
            'user', 'referral', 'offer', 'order'
        ).order_by('-created_at')
        
        # Apply search filter
        if search:
            rewards = rewards.filter(
                Q(user__email__icontains=search) |
                Q(user__full_name__icontains=search) |
                Q(referral__referrer__email__icontains=search)
            )
        
        # Apply status filter
        now = timezone.now()
        if status_filter == 'available':
            rewards = rewards.filter(
                is_used=False,
                valid_from__lte=now,
                valid_until__gte=now
            )
        elif status_filter == 'used':
            rewards = rewards.filter(is_used=True)
        elif status_filter == 'expired':
            rewards = rewards.filter(
                is_used=False,
                valid_until__lt=now
            )
        
        # Apply reward type filter
        if reward_type:
            rewards = rewards.filter(reward_type=reward_type)
        
        # Pagination
        page = request.GET.get('page', 1)
        paginator = Paginator(rewards, 20)
        rewards_page = paginator.get_page(page)
        
        context = {
            'rewards': rewards_page,
            'search': search,
            'status_filter': status_filter,
            'reward_type': reward_type,
        }
        
        return render(request, 'admin_panel/referrals/rewards.html', context)


class UserReferralDetailView(AdminLoginMixin, View):
    """View detailed referral information for a specific user"""
    
    def get(self, request, user_id):
        user = get_object_or_404(Register, pk=user_id)
        
        # Get referral code
        try:
            referral_code = ReferralCode.objects.get(user=user)
        except ReferralCode.DoesNotExist:
            referral_code = None
        
        # Referrals made by this user
        referrals_made = Referral.objects.filter(
            referrer=user
        ).select_related('referred').order_by('-signed_up_at')
        
        # If this user was referred
        referred_by = None
        try:
            referred_by = Referral.objects.get(referred=user)
        except Referral.DoesNotExist:
            pass
        
        # Rewards earned
        rewards_earned = ReferralReward.objects.filter(
            user=user
        ).select_related('offer', 'order').order_by('-created_at')
        
        # Statistics
        successful_count = referrals_made.filter(
            first_purchase_at__isnull=False
        ).count()
        
        pending_count = referrals_made.filter(
            first_purchase_at__isnull=True
        ).count()
        
        context = {
            'user': user,
            'referral_code': referral_code,
            'referrals_made': referrals_made,
            'referred_by': referred_by,
            'rewards_earned': rewards_earned,
            'total_earnings': user.total_referral_earnings or Decimal('0'),
            'successful_referrals': successful_count,
            'pending_referrals': pending_count,
        }
        
        return render(request, 'admin_panel/referrals/user_detail.html', context)