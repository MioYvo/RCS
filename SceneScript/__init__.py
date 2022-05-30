import loguru

from SceneScript.register import scripts_manager
from SceneScript.exchange.withdraw import (
    exchange_withdraw_without_recharge,
    exchange_withdrawal_amount_limit,
    exchange_withdrawal_amount_per_time_limit,
    exchange_withdrawal_num_per_time_limit,
    exchange_multi_stellar_address_withdraw_to_one
)
from SceneScript.exchange.recharge import (
    exchange_recharge_amount_per_time_limit,
    exchange_recharge_num_per_time_limit,
    exchange_recharge_amount_limit,
    exchange_recharge_multi_stellar_address_to_one,
)
from SceneScript.lland.withdraw import (
    lland_withdraw_without_recharge,
    lland_withdrawal_amount_limit,
    lland_withdrawal_amount_per_time_limit,
    lland_withdrawal_num_per_time_limit,
    lland_multi_address_withdraw_to_one,
    lland_withdrawal_contract_addr_num_per_time_limit,
)
from SceneScript.lland.recharge import (
    lland_recharge_amount_per_time_limit,
    lland_recharge_num_per_time_limit,
)

loguru.logger.info('registering')
#                   withdraw
# exchange
scripts_manager.register(exchange_withdrawal_amount_limit)
scripts_manager.register(exchange_withdrawal_amount_per_time_limit)
scripts_manager.register(exchange_withdrawal_num_per_time_limit)
scripts_manager.register(exchange_multi_stellar_address_withdraw_to_one)
scripts_manager.register(exchange_withdraw_without_recharge)
# lland
scripts_manager.register(lland_withdraw_without_recharge)
scripts_manager.register(lland_withdrawal_amount_per_time_limit)
scripts_manager.register(lland_withdrawal_num_per_time_limit)
scripts_manager.register(lland_withdrawal_contract_addr_num_per_time_limit)
scripts_manager.register(lland_multi_address_withdraw_to_one)

#                   recharge
# exchange
scripts_manager.register(exchange_recharge_amount_limit)
scripts_manager.register(exchange_recharge_amount_per_time_limit)
scripts_manager.register(exchange_recharge_num_per_time_limit)
scripts_manager.register(exchange_recharge_multi_stellar_address_to_one)
# lland
scripts_manager.register(lland_recharge_amount_per_time_limit)
scripts_manager.register(lland_recharge_num_per_time_limit)
