Feature: Login to the game.

  Scenario: Login with correct password
    Given The player "Bob" exists with password "test"
    When I login as "Bob" with password "test"
    Then I should see "connected"
