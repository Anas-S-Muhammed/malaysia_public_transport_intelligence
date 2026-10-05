# Tableau calculations

Connect to `data/processed/tableau_ridership.csv`. Set Date to Date, Ridership to Number (whole), and Is Observed / Is Weekend to Boolean. Field names below assume Tableau's space-separated display names; rename imported underscore fields accordingly. Counts are headline rides, not unique people. Preserve nulls.

## Basic measures

**Total Ridership**
```tableau
SUM([Ridership])
```

**Average Daily Ridership** (selected services combined per observed calendar date)
```tableau
SUM([Ridership]) / COUNTD(IF [Is Observed] THEN [Date] END)
```
This is different from `AVG([Ridership])`, which averages service-day rows. For comparisons, restrict dates/services to a common complete observation window.

**Week Type**
```tableau
IF [Is Weekend] THEN "Weekend" ELSE "Weekday" END
```
Weekday does not mean a working day: holidays are not included.

**Core Basket**
```tableau
[Service Code] = "rail_lrt_ampang"
OR [Service Code] = "rail_mrt_kajang"
OR [Service Code] = "rail_lrt_kj"
OR [Service Code] = "rail_monorail"
```

## Complete monthly comparisons

Use discrete continuous-calendar month marks, with Service partitioning the table calculation. Keep missing months visible; do not filter them out before computing comparisons. Use the observation mask because Tableau ignores null counts by default.

**Complete Month**
```tableau
COUNT([Ridership]) = DAY(DATEADD('day', -1,
    DATEADD('month', 1, DATETRUNC('month', MIN([Date])))))
```
This formula is valid at **one service per calendar month**. It also prevents treating the partial last month of a future extract as complete. For totals across several services, use the fixed basket with verified complete coverage or separately validate each service-month.

**Comparable Monthly Ridership**
```tableau
IF [Complete Month] THEN SUM([Ridership]) END
```

**Previous Year Ridership**
```tableau
LOOKUP([Comparable Monthly Ridership], -12)
```

**YoY Growth**
```tableau
IF NOT ISNULL([Previous Year Ridership]) AND [Previous Year Ridership] > 0
THEN [Comparable Monthly Ridership] / [Previous Year Ridership] - 1
END
```
Format as Percentage. Compute using Month, partition by Service, with one mark for each calendar month. Twelve marks must represent twelve calendar months. Keep the prior year in the calculation partition; use a table calculation display filter for the visible year rather than an ordinary year filter. Annual views require an independently checked complete year and a `-1` offset; do not reuse `-12` there.

**Growth Classification**
```tableau
IF ISNULL([YoY Growth]) THEN "Comparison unavailable"
ELSEIF [YoY Growth] > 0.05 THEN "Growing"
ELSEIF [YoY Growth] < -0.05 THEN "Declining"
ELSE "Within 5%"
END
```
The 5% bands are presentation choices, not significance tests.

## Rolling trend and contribution

**Rolling Average (30 days)**
```tableau
IF WINDOW_COUNT(SUM([Ridership]), -29, 0) = 30
THEN WINDOW_AVG(SUM([Ridership]), -29, 0)
END
```
Use one mark per exact Date. Compute along Date, partition by Service. Show missing dates. For an aggregate basket, verify complete service coverage separately: a non-null SUM does not prove all selected services reported.

**Service Share**
```tableau
SUM([Ridership]) / WINDOW_SUM(SUM([Ridership]))
```
Compute across Service within the same period. It is a share of the displayed services' reported rides; filtering services changes the denominator. Do not label it national market share.

## Parameter

Create string parameter **Selected Metric** with values `Total rides`, `Daily average`, and `YoY growth`.

**Selected Metric Value** (monthly service view)
```tableau
CASE [Selected Metric]
WHEN "Total rides" THEN SUM([Ridership])
WHEN "Daily average" THEN SUM([Ridership]) / COUNTD(IF [Is Observed] THEN [Date] END)
WHEN "YoY growth" THEN [YoY Growth]
END
```
Switch the title and number formatting with the metric. Use separate sheets for count and percentage formats if the workbook cannot change formatting reliably. Do not sum the selected metric across services when it represents growth.
