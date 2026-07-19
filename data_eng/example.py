from district_rollup import build_district_table, rank_deserts

fac = spark.table("databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities")
pincodes = spark.table("databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.india_post_pincode_directory")
nfhs = spark.table("databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.nfhs_5_district_health_indicators")

district = build_district_table(fac, pincodes, nfhs, "maternity")   # the planner's dropdown choice
district.groupBy("verdict").count().show()          # sanity: how many of each state?
display(district)                                   # the map-ready table

# persist for the app to read (don't recompute live in the demo)
district.write.mode("overwrite").saveAsTable("workspace.default.district_maternity")

rank_deserts(district).show(20, truncate=False)     # worst deserts -> the ranked-list panel
