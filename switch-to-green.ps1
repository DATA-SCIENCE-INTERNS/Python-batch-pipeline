$ErrorActionPreference = "Stop"
$projectDirectory = "C:\Users\ekica\Documents\python pipeline\Python-batch-pipeline"
$yellowContainer = "taxi_backfill_2025"
$greenContainer = "green_backfill_2025"

Set-Location -LiteralPath $projectDirectory

while ($true) {
    $status = docker exec nyc_taxi_postgres psql -U taxi_user -d nyc_taxi -At `
        -c "SELECT status FROM pipeline.batch_runs WHERE run_id=38;"

    if ($status -eq "success") {
        break
    }
    if ($status -eq "failed") {
        throw "Yellow March run 38 failed; Green handoff was not started."
    }
    Start-Sleep -Seconds 15
}

docker stop --time 15 $yellowContainer

docker exec nyc_taxi_postgres psql -U taxi_user -d nyc_taxi -c `
    "UPDATE pipeline.batch_runs SET status='failed', finished_at=now(), error_message='Stopped after Yellow March to switch to Green-only backfill' WHERE taxi_type='yellow' AND status='running';"

docker rm $yellowContainer

docker compose run -d --name $greenContainer pipeline backfill `
    --taxi-type green --start 2025-02 --end 2025-12

"Green handoff completed at $(Get-Date -Format o)"
