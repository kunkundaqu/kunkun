class TradingRecord(models.Model):
    ASSET_TYPE_CHOICES = [
        ('crypto', '加密货币'),
        ('stock', '股票'),
        ('forex', '外汇'),
        ('commodity', '大宗商品'),
    ]
    
    DIRECTION_CHOICES = [
        ('long', '做多'),
        ('short', '做空'),
    ]
    
    STATUS_CHOICES = [
        ('open', '持仓中'),
        ('closed', '已平仓'),
    ]
    
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPE_CHOICES, verbose_name='资产类型')
    symbol = models.CharField(max_length=20, verbose_name='交易品种')
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES, verbose_name='交易方向')
    quantity = models.DecimalField(max_digits=20, decimal_places=8, verbose_name='数量')
    entry_price = models.DecimalField(max_digits=20, decimal_places=8, verbose_name='入场价格')
    exit_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True, verbose_name='出场价格')
    entry_time = models.DateTimeField(verbose_name='入场时间')
    exit_time = models.DateTimeField(null=True, blank=True, verbose_name='出场时间')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open', verbose_name='状态')
    current_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True, verbose_name='当前价格')
    notes = models.TextField(blank=True, null=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '交易记录'
        verbose_name_plural = '交易记录'
        ordering = ['-entry_time']

    def __str__(self):
        return f"{self.get_asset_type_display()} - {self.symbol} - {self.get_direction_display()}" 