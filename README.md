# Payment Link XBlock

![https://github.com/eol-uchile/payment_link_xblock/actions](https://github.com/eol-uchile/payment_link_xblock/workflows/Python%20application/badge.svg)

# Install

    docker-compose exec cms pip install -e /openedx/requirements/payment_link_xblock
    docker-compose exec lms pip install -e /openedx/requirements/payment_link_xblock

## TESTS
**Prepare tests:**

    > cd .github/
    > docker-compose run --rm lms /openedx/requirements/payment_link_xblock/.github/test.sh

## Notes

- Need Course Mode Verified SKU configurated to show the link

