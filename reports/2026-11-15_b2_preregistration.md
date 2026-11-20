# B2 pre-registration: the two-exchange order path (C550), written before any of its code

Build step B2 of `reports/2026-10-04_live_march_roadmap.md` (routine `trig_01XjNNKCDMzqwQjXGge7753r`, fired 15 Nov 2026
04:17 UTC). Committed and pushed **before** the order path is written. Every test below is fixed here and is not
loosened after a result. A test that cannot pass is reported as failed, not rewritten.

## What was found first (15 Nov, before writing the tests)

- **The new CoinDCX read-only key works.**
  - The C540 line reads again from 6 Nov 11:38 IST (rupee wallet ₹0.07, 0 positions), and has read every hour since.
  - Delta reads too.
- **Delta India: cross margin exists, but the API cannot show it on an empty account.**
  - Delta's India guide says "All contracts support Cross Margin mode". Margin mode is an account-level setting,
    changed only with no open positions or orders.
  - The API's change-mode request lists only `isolated` and `portfolio`. The wallet has a field `cross_position_margin`.
    Nothing a read key can call shows the current mode while the account holds nothing: `/v2/users/trading_preferences`
    has no mode field, and positions carry `margin_mode` only once they exist.
  - **The mode is therefore confirmed by the operator in Delta's app, then checked on the first real fill.**
- **CoinDCX: its API documentation says cross margin is NOT supported on INR-margined futures.**
  - In three places: "Cross margin mode is only supported on USDT margined Futures at the moment"; "Cross margin mode
    is not supported on INR margined Futures".
  - A help-centre article (updated about 4 months ago) lists "Margin Type (INR or USDT)" and "Isolated or Cross Margin"
    without that restriction. The two disagree.
  - **This is not confirmed on the operator's account.** Per the routine, *the order path must not go live until it is
    solved*. C550 is built so that it cannot.
- **CoinDCX futures orders have no client order id and no reduce-only flag** (create-order fields: side, pair,
  order_type, price, stop_price, total_quantity, leverage, notification, time_in_force, margin_currency_short_name,
  position_margin_type).
  - Its own **exit-position** call closes a whole position and can never open one.
  - A position's **stop loss** (`positions/create_tpsl`) closes the whole position.
  - Stop orders show `stop_trigger_instruction: "last_price"`; no mark-price trigger is documented.
- **Delta India orders:** `client_order_id` (max 32, unique among open orders), `reduce_only`, `stop_order_type`
  `stop_loss_order` with `stop_trigger_method` `mark_price`, `GET /v2/orders/client_order_id/{client_oid}`. Error shape
  `{success:false, error:{code}}`; the signature is valid for 5 s.
- **Rupee rates, live and keyless:**
  - Delta `/v2/settings` `fiat_to_usd.asset_to_fiat_value` = **85**;
  - CoinDCX `/api/v1/derivatives/futures/data/conversions` `USDTINR conversion_price` = **102.0** (last changed
    26 May 2026; "may change periodically due to extreme market movements").

## The tests (`omega_c550_test.py`, mocked exchanges; no real request is ever made)

**A. The lock and the dry run**
- T1. `C550_LIVE_OK` exists, defaults to **False**, and is separate from `C488_LIVE_OK` (which stays False). With it
  False, a whole day (entries, exits, stops, the watch, the kill switch) builds and logs every order and **sends none**:
  the network functions raise if touched.
- T2. Even with `C550_LIVE_OK` True, nothing is sent unless all of these hold; otherwise the open is refused and the
  reason logged:
  - both exchanges' keys read successfully within the last hour;
  - both rupee rates were read live just now;
  - cross margin confirmed for both exchanges (`C550_CROSS_CONFIRMED`, set only after the operator's confirmation);
  - the CoinDCX market is not `exit_only`.

**B. The orders, built right**
- T3. Delta entry:
  - `product_symbol`, an integer `size` = the paper ledger's whole contracts, `side`, `market_order`, `reduce_only`
    false;
  - a `client_order_id` ≤ 32 characters derived from the day, coin, leg and action, the same on a re-run;
  - the signature exactly as `_c540_delta_sign` (method + timestamp + path + query + body).
- T4. CoinDCX entry:
  - `pair` `B-<COIN>_USDT`, `margin_currency_short_name` `INR`, `position_margin_type` `crossed`, no `time_in_force`
    on a market order;
  - `total_quantity` = Delta's dollar notional × (Delta's rate ÷ CoinDCX's rate) ÷ price, rounded down to the
    instrument's `quantity_increment` and ≥ its `min_notional`;
  - the signature = HMAC-SHA256 of the compact JSON body (`_c540_dcx_sign`).
- T5. Rupee parity:
  - the two legs' rupee values agree within one quantity step;
  - both rates come from the live reads (85 and 102 in the fixture; a changed CoinDCX rate changes the quantity);
  - an unreadable rate means nothing is opened.
- T6. Exits: Delta closes with `reduce_only` true and the exact size; CoinDCX uses its exit-position call. No exit order
  can open a position.

**C. Two legs together**
- T7. The CoinDCX leg is placed first. Delta's is placed only after the CoinDCX fill has been read back.
- T8. CoinDCX refuses or rejects the order (close-only market, HTTP 422, an `exit_only` flag): Delta's leg is never
  sent, and the refusal is logged.
- T9. CoinDCX fills and Delta's order fails: the CoinDCX leg is unwound at once (exit-position), logged and alerted.
- T10. A partial CoinDCX fill: Delta's leg is sized to the filled rupee value in whole contracts. Under one contract, the
  CoinDCX leg is unwound.
- T11. A send times out: the state is read back (Delta by client order id; CoinDCX by open orders and positions) before
  any retry. An order is never doubled.

**D. The safety net (the operator's choice (b), 23 Oct)**
- T12. The emergency stop on every short leg sits at mark × (1 + (account − 0.25 × half) ÷ leg notional):
  - on Delta, `stop_loss_order`, `reduce_only`, `stop_trigger_method` `mark_price`;
  - on CoinDCX, the position's stop loss (trigger as CoinDCX documents it: last price);
  - re-placed at each daily run and when the account or the leg changes, with the old one cancelled first.
- T13. A BLESS-size +530% jump on a short leg:
  - the stop fires (or the exchange liquidates first);
  - within the next watch (60 s) the twin is closed (reduce-only on Delta, exit-position on CoinDCX);
  - both legs are journalled with `why` = 'emergency stop' or 'liquidated';
  - the account alert fires.
- T14. A liquidation or auto-deleveraging fill found by the watch leads to the same twin close.

**E. Restart safety**
- T15. A re-run of the same day after a restart sends nothing twice. Delta: the same client order ids. Both: the
  write-ahead intent record in `data/c550_orders.json` and a read of the positions.
- T16. The process killed between the two legs of an entry: at boot, before anything else, the lone CoinDCX leg is
  found and closed, and it is logged.
- T17. The process killed between the two legs of an exit: at boot the remaining leg is closed.

**F. The watch, the reconciliation, the kill switch, the keys**
- T18. Hourly: exchange positions against the live ledger. An unexplained difference is an alert. In the dry run, the
  real accounts are empty and the line says they match.
- T19. The kill switch (the file `data/c550_kill`): every order is cancelled and every leg closed on both exchanges, and
  nothing new opens until the file is removed.
- T20. An expired or refused key on either exchange (the C540 reason line, e.g. "API key expired"): nothing new opens,
  closes are still attempted, and the operator is alerted.
- T21. The margin watch reads the REAL balances (C540's reads). In the dry run it states them (0) beside the paper's.
- T22. A CoinDCX fill with `position_margin_type` other than `crossed`, or a Delta position with `margin_mode`
  `isolated`: no further opens, and an alert.

**G. The tax journal**
- T23. A live close writes a `close` record with exactly the paper ledger's keys (`_c544_close`):
  - real fill prices;
  - fees split into fee and GST;
  - rent by the IST month of each payment, from the exchanges' own funding records (Delta's via `_c549_paid`);
  - `why` = 'emergency stop' or 'liquidated' when so;
  - `omega_tax_statement.py --live` (its `build`) reads the resulting ledger without error.

**H. In the bot**
- T24. After the plan's daily run, C550 (dry):
  - logs every order it would send for that day's exits and entries (CoinDCX first);
  - logs each short leg's emergency-stop price;
  - leaves the paper ledger identical, before and after.
- T25. The older tests stay green (c544-c549 included) and the full battery passes.
- T26. C540's read-only client is unchanged in what it may call. C550's order classes are separate and refuse any path
  not on their own list.

## Not in B2

- **Sending real orders.** The lock stays off; B3 (15 Dec) runs the dry path daily on the server and compares it with
  paper.
- **Choosing an alternative if CoinDCX's rupee futures cannot use cross margin.** That is the operator's decision with
  numbers: options are set out in the B2 report and need a pre-registered research round before any change to the
  plan.
