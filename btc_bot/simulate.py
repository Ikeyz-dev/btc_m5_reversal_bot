def simulate_trade(
    df: pd.DataFrame,
    entry_index: int,
    direction: Direction,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    time_column: str = "timestamp",
    fee_pct: float = 0.0,
    slippage_pct: float = 0.0,
) -> Optional[TradeResult]:
    """
    Simulate a single trade forward from entry_index (the candle whose
    OPEN is the entry price) until SL or TP is hit.

    fee_pct and slippage_pct are PER-SIDE percentages (e.g. 0.05 = 0.05%).
    Round-trip cost (entry + exit, both sides) is deducted from the
    result in R terms, so profit_factor/expectancy reflect real costs.
    """
    risk_distance = abs(entry_price - stop_loss)
    if risk_distance <= 0:
        raise ValueError("Stop loss distance must be greater than zero.")

    round_trip_cost_pct = 2 * (fee_pct + slippage_pct) / 100.0
    cost_amount = entry_price * round_trip_cost_pct
    cost_in_r = cost_amount / risk_distance

    for i in range(entry_index, len(df)):
        row = df.iloc[i]
        high, low = row["high"], row["low"]

        if direction == "BUY":
            hit_sl = low <= stop_loss
            hit_tp = high >= take_profit
        elif direction == "SELL":
            hit_sl = high >= stop_loss
            hit_tp = low <= take_profit
        else:
            raise ValueError(f"Unknown direction: {direction}")

        if hit_sl:
            r_multiple = -1.0 - cost_in_r
            return TradeResult(
                exit_price=stop_loss,
                exit_time=row[time_column],
                exit_index=i,
                result="WIN" if r_multiple > 0 else "LOSS",
                r_multiple=r_multiple,
                reason="SL",
            )
        if hit_tp:
            reward_distance = abs(take_profit - entry_price)
            r_multiple = (reward_distance / risk_distance) - cost_in_r
            return TradeResult(
                exit_price=take_profit,
                exit_time=row[time_column],
                exit_index=i,
                result="WIN" if r_multiple > 0 else "LOSS",
                r_multiple=r_multiple,
                reason="TP",
            )

    return None  # trade still open at end of data    for i in range(entry_index, len(df)):
        row = df.iloc[i]
        high, low = row["high"], row["low"]

        if direction == "BUY":
            hit_sl = low <= stop_loss
            hit_tp = high >= take_profit
        elif direction == "SELL":
            hit_sl = high >= stop_loss
            hit_tp = low <= take_profit
        else:
            raise ValueError(f"Unknown direction: {direction}")

        if hit_sl and hit_tp:
            # Conservative assumption: SL occurred first.
            return TradeResult(
                exit_price=stop_loss,
                exit_time=row[time_column],
                exit_index=i,
                result="LOSS",
                r_multiple=-1.0,
                reason="SL",
            )
        if hit_sl:
            return TradeResult(
                exit_price=stop_loss,
                exit_time=row[time_column],
                exit_index=i,
                result="LOSS",
                r_multiple=-1.0,
                reason="SL",
            )
        if hit_tp:
            reward_distance = abs(take_profit - entry_price)
            r_multiple = reward_distance / risk_distance
            return TradeResult(
                exit_price=take_profit,
                exit_time=row[time_column],
                exit_index=i,
                result="WIN",
                r_multiple=r_multiple,
                reason="TP",
            )

    return None  # trade still open at end of data
