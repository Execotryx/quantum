"""Install the exact lower-workspace tail and cheaper extraction self-products."""
def install():
    import compact_h_filter,self_products
    compact_h_filter.install()
    self_products.install()
    return {'compact_h_filter':True,'specialized_gold_self_products':True,'reused_top_update_word':True}
