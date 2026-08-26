# Design decisions

- The project uses classical digital image processing methods only. Deep
  learning is outside the course-project scope.
- The planned system combines three complementary cues: SIFT copy-move
  matching, JPEG ghost analysis, and JPEG block-grid inconsistency analysis.
- Equal fusion weights are the initial baseline. Any tuned weights must use the
  validation split only and must be documented.
- Results will be delivered through a command-line workflow and static HTML
  reports. A web application and backend are not planned.
- Implementation begins only after the team approves the requirements.
