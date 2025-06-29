def stringify_keys(obj):
    """
    Converte ricorsivamente tutte le chiavi di un dict in stringhe.
    Funziona anche con liste annidate.
    """
    if isinstance(obj, dict):
        return {str(k): stringify_keys(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [stringify_keys(i) for i in obj]
    else:
        return obj
