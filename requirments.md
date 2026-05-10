  Fix and enhance the Google Sheet integration screen with the following requirements:

  1. Link verification — When a user shares a Google Sheet link, the system must verify
   whether it has read access to that sheet. Display a clear success or error message
  based on the result.
  2. Column validation — If access is confirmed, validate that the sheet contains the
  required columns: SKU and Product Link. Show an error if either column is missing.
  3. Direct file upload — Add an option for users to directly upload a sheet file
  (e.g., .xlsx or .csv) as an alternative to sharing a link.
  4. Template download — Add a "Download Template" button to the UI that provides a
  pre-formatted file users can fill in with the required columns before uploading.
  5. Fetched data preview —
  Once the sheet is
  successfully accessed and
  parsed, display the fetched
  product records in the UI,
  showing all available column
   details (e.g., SKU, Product
   Link, and any additional
  columns present in the
  sheet).
  6. Refresh/Update list —
  Provide an "Update List"
  button that allows the user
  to re-fetch the latest data
  from the sheet and refresh
  the displayed records.