from enum import Enum


class UserTypeSubscription:
    """
    This object represents a type of User subscription
    """

    ADVERTISEMENT = 'ads'
    AUCTION = 'auction'


class GroupTypeSubscription:
    """
    This object represents a type of Group subscription
    """

    ADVERTISEMENT = 'ads'
    AUCTION = 'auction'
    FREE_TRIAL = 'free_trial'

    @staticmethod
    async def get_by_product_category(category):
        data = {
            ClientProductCategory.AUCTION: GroupTypeSubscription.AUCTION,
            ClientProductCategory.ADVERTISEMENT: GroupTypeSubscription.ADVERTISEMENT,
            AdminProductCategory.AUCTION: GroupTypeSubscription.AUCTION,
            AdminProductCategory.ADVERTISEMENT: GroupTypeSubscription.ADVERTISEMENT,
        }
        return data.get(category)


class ClientProductCategory:
    AUCTION = 'CLIENT_AUCTION'
    ADVERTISEMENT = 'CLIENT_ADVERTISEMENT'


class AdminProductCategory:
    AUCTION = 'ADMIN_AUCTION'
    ADVERTISEMENT = 'ADMIN_ADVERTISEMENT'

    @staticmethod
    async def get_by_func_type(func_type):
        data = {GroupTypeSubscription.AUCTION: AdminProductCategory.AUCTION,
                GroupTypeSubscription.ADVERTISEMENT: AdminProductCategory.ADVERTISEMENT}
        return data.get(func_type)
