import json
from json.decoder           import JSONDecodeError
from enum                   import Enum

from django.views           import View
from django.http            import JsonResponse
from django.db              import transaction
from django.db.models       import Q
from django.core.exceptions import ValidationError

from deals.models           import (
    Account,
    Deal2020,
    Deal2021, 
    DealPosition
)
from users.utils            import login_decorator

class DealPositionId(Enum):
    DEPOSIT  = 1
    WITHDRAW = 2

class CheckError():   
    def check_deal_position_id(deal_position_id):
        if not DealPosition.objects.filter(id = deal_position_id).exists():
            raise DealPosition.DoesNotExist
    
    def check_account_id(account_id):
        if not Account.objects.filter(id = account_id).exists():
            raise Account.DoesNotExist

    def check_amount_validation(amount):
        if amount <= 0:
            raise ValidationError('INVALID_AMOUNT')
    
class DealView(View):
    #입금, 출금
    @login_decorator
    def post(self, request, account_id):
        try:
            data             = json.loads(request.body)
            deal_position_id = int(data['deal_position_id'])
            amount           = int(data['amount'])
            description      = data.get('description')
            user             = request.user

            CheckError.check_account_id(account_id)
            CheckError.check_deal_position_id(deal_position_id)
            CheckError.check_amount_validation(amount)

            account = Account.objects.get(id = account_id)

            if not account.owner_id == user.id:
                return JsonResponse({'message' : 'INVALID_ACCOUNT_ID'}, status = 400)
            
            before_balance = account.balance

            with transaction.atomic():
                if deal_position_id == DealPositionId.DEPOSIT.value:
                    last_balance    = account.balance + amount
                    account.balance = last_balance
                    account.save()
                
                if deal_position_id == DealPositionId.WITHDRAW.value:
                    if amount > account.balance:
                        return JsonResponse({'message' : 'INSUFFICIENT_BALANCE'}, status = 400)
                    
                    last_balance    = account.balance - amount
                    account.balance = last_balance
                    account.save()
            
                Deal2021.objects.create(
                    account_id       = account_id,
                    deal_position_id = deal_position_id,
                    amount           = amount,
                    description      = description,
                    balance          = account.balance
                )
            
            after_balance = account.balance
            
            return JsonResponse({'before_balance' : before_balance, 'after_balance' : after_balance}, status=201)
                   
        except KeyError :
            return JsonResponse({'message' : 'KEY_ERROR'}, status=400)
        
        except JSONDecodeError:
            return JsonResponse({'message' : 'JSON_DECODE_ERROR'}, status = 400)
        
        except Account.DoesNotExist:
            return JsonResponse({'message' : 'ACCOUNT_DOES_NOT_EXIST'}, status = 404)
        
        except DealPosition.DoesNotExist:
            return JsonResponse({'message' : 'INVALID_DEAL_POSITION_ID'}, status = 400)
        
        except ValidationError as e:
            return JsonResponse({'message' : (e.message)}, status = 400)
    
    #거래내역 조회
    @login_decorator
    def get(self, request, account_id):
        try:
            CheckError.check_account_id(account_id)
            
            account = Account.objects.get(id = account_id)
            user    = request.user

            if not account.owner_id == user.id:
                return JsonResponse({'message' : 'INVALID_ACCOUNT_ID'}, status = 400)

            start_date       = request.GET['start_date']
            end_date         = request.GET['end_date']
            sort             = request.GET.get('sort')
            deal_position_id = request.GET.get('deal_position_id')
            page             = int(request.GET.get('page', 1))
            start_year       = int(start_date.split('-')[0])
            
            page_size = 20
            limit     = page_size * page
            offset    = limit - page_size

            sort_by = {
                'recent' : '-created_at',
                'old'    : 'created_at'
            }
            
            deal_filter = (Q(created_at__date__range = (start_date, end_date)) & Q(account_id = account_id))

            if deal_position_id:
                CheckError.check_deal_position_id(deal_position_id)
                
                deal_filter.add(Q(deal_position_id = deal_position_id), Q.AND)
            
            data2020 = []
            
            if start_year == 2020:
                deals2020 = Deal2020.objects.select_related('deal_position').filter(deal_filter).order_by(sort_by.get(sort, '-created_at'))

                data2020 = [{
                'id'            : deal.id,
                'deal_position' : deal.deal_position.position,
                'deal_date'     : deal.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'deal_amount'   : deal.amount,
                'deal_balance'  : deal.balance,
                'description'   : deal.description,
                } for deal in deals2020]
            
            deals2021 = Deal2021.objects.select_related('deal_position').filter(deal_filter).order_by(sort_by.get(sort, '-created_at'))

            data2021 = [{
                'id'            : deal.id,
                'deal_position' : deal.deal_position.position,
                'deal_date'     : deal.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'deal_amount'   : deal.amount,
                'deal_balance'  : deal.balance,
                'description'   : deal.description,
                } for deal in deals2021]
            
            data = data2021 + data2020 if sort_by.get(sort, '-created_at') == '-created_at' else data2020 + data2021

            return JsonResponse({'data' : data[offset:limit]}, status = 200)
        
        except KeyError:
            return JsonResponse({'message' : 'KEY_ERROR'}, status = 400)
        
        except ValidationError:
            return JsonResponse({'message' : 'INVALID_DATE'}, status = 400)
        
        except Account.DoesNotExist:
            return JsonResponse({'message' : 'ACCOUNT_DOES_NOT_EXIST'}, status = 404)
        
        except DealPosition.DoesNotExist:
            return JsonResponse({'message' : 'INVALID_DEAL_POSITION_ID'}, status = 400)