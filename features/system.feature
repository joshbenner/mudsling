Feature: System essentials.

  Scenario: Enabled plugins.
    Given admin is connected
    When admin enters ";game.plugins.enabled_plugins()"
    Then admin should see "mudslingcore"
    And admin should see "defaultloginscreen"
