Feature: Mail
  As a player
  I want to exchange mail with other players
  so I can communicate asynchronously

  Scenario: Player has no mail
    Given Alice is connected
    When Alice enters "@mail"
    Then Alice should see "0 messages"
    And Alice should see "(no messages found matching query)"

  Scenario: Quick mail to invalid recipient
    Given Alice is connected
    When Alice enters "@mail/quick foo=Test"
    Then Alice should see "No recipient called 'foo' was found."

  Scenario: Player sends quick mail
    Given Alice and Bob are connected
    When Alice enters "@mail/quick bob/Test Subject=This is my test message"
    And Bob enters "@mail"
    And Bob enters "@mail/read 1"
    Then Alice should see "Mail sent to Bob."
    And Bob should see "You have new mail (1) from Alice."
    And Bob should see "@mail: 1 message"
    And Bob should see "Alice"
    And Bob should see "Test Subject"
    And Bob should see "Message 1"
    And Bob should see "From:  Alice"
    And Bob should see "To:  Bob"
    And Bob should see "Subject:  Test Subject"
    And bob should see "This is my test message"

  Scenario: Quick forward message
    Given Alice and Bob are connected
    When Alice enters "@mail/quick bob/Test Subject=This is my test message"
    And Bob enters "@mail/quickforward 1 to alice"
    And Alice enters "@mail/read 1"
    Then Bob should see "Mail sent to Alice."
    And Alice should see "You have new mail (1) from Bob."
    And Alice should see "Subject:  FWD: Test Subject"
    And Alice should see "> This is my test message"

  Scenario: Quick reply
    Given Alice and Bob are connected
    When Alice enters "@mail/quick bob/Test Subject=This is my test message"
    And Bob enters "@mail/quickreply 1=This is my reply"
    And Alice enters "@mail/read 1"
    Then Bob should see "Mail sent to Alice."
    And Alice should see "You have new mail (1) from Bob."
    And Alice should see "Subject:  RE: Test Subject"
    And Alice should see "> This is my test message"
    And Alice should see "This is my reply"

  Scenario: Mail editor
    Given Alice and Bob are connected
    When Alice enters "@mail/send bob=Test Subject"
    And Alice enters "'First line of text"
    And Alice enters "'Second line of text"
    And Alice enters ".send"
    And Bob enters "@mail/read 1"
    Then Alice should see "Mail sent to Bob."
    And Bob should see "You have new mail (1) from Alice."
    And Bob should see "First line of text"
    And Bob should see "Second line of text"