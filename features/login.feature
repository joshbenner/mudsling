Feature: Login to the game.

  Scenario: Login with correct password
    Given The player "Bob" exists with password "test"
    When I enter "connect bob test"
    Then I should see "Connected to player Bob."

  Scenario: Fail to login with incorrect password
    Given The player "Bob" exists with password "test"
    When I enter "connect bob incorrect"
    Then I should see "Unknown player name or password."
