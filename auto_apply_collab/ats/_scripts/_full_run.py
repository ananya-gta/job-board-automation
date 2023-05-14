import time

import _apply_job as apply
import _auto_answer_aq as answer
import _parse_aq as aq

# apply_url = "https://www.careerbuilder.com/job/J3Q1XZ6CGYVML41JS9P?apply=yes"
if __name__ == "__main__":
    url_filename = "urls.txt"
    with open(url_filename) as f:
        for apply_url in f.readlines():
            apply_url = apply_url.strip()
            print('*'*600)
            print(f"Starting run for URL {apply_url}")
            print(f"{'-'*200}")
            try:
                aq_status = aq.main(apply_url)["questions"]
                print(f"{'-' * 200}")
            except Exception as e:
                print('*'*200)
                print(f"Since Exception occured , we will skip this url. Just make sure error message is appropriate like 'Job already applied / Job Expired' etc.")
                # print(e)
                print('*'*200)

            # This means job is already applied or expired or something else that caused error status
            if isinstance(aq_status, dict):
                print('-'*200)
                print(f"AQ status: {aq_status}")
                print('-'*200)
                print(f"There was ERROR skipping this job.")
                # print('-'*200)
                print('Next JOB in 5 seconds')
                # print('-'*200)
                print('*'*200)
                time.sleep(5)
                continue

            # This means status was not error, we can proceed to answer AQ
            # Generate answer in answer.json
            answer.main()

            # Start apply job process
            apply_status = apply.main(apply_url)
            print(f"{aq_status=}\n{apply_status=}")
            print('*'*200)
            time.sleep(5)
